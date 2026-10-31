"""Canlı güvenlik denemesi: çalışan sisteme web (nginx) üzerinden 27 olumsuz istek atar, hepsinin
reddedildiğini doğrular. Yalnız kendi yerel/izinli kurulumunuzda çalıştırın.

Ne dener: güvenlik başlıkları, CORS, girişsiz ve sahte belirteçli istek (401), rol dışı iş (403), SQL
enjeksiyonu, girdi doğrulama (422), açık posta rölesi ve e-posta başlık enjeksiyonu (422), 2 MB gövde
(413) ve sahte IP başlıklarıyla kaba kuvvet (10 denemeden sonra 429).
Veri değiştirmez; yalnız kaba kuvvet denemesi bir "Art arda hatalı giriş" alarmı, denetim kaydı ve
yöneticiye uyarı e-postası bırakır (beklenen davranış). Şifre ya da belirteç yazdırmaz.
Demo hesaplarını kullanır (SEED_PROFILE=demo, README'deki tablo).

Kullanım (depo kökünden): sh scripts/guvenlik_denemesi.sh — yeniden çalıştırmadan önce 5 dakika bekleyin
(giriş sınırı aynı kapsayıcı adresini 5 dakika kilitli tutar).
"""

import json
import secrets
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
WEB = sys.argv[1].rstrip("/")
API = WEB + "/api/v1"
DEMO = {  # README'de yazılı yerel demo hesapları (SEED_PROFILE=demo)
    "yonetici": "yonetici123",
    "depo1": "depo1234",
    "magaza1": "magaza123",
    "satis1": "satis123",
}
results: list[tuple[str, bool, str]] = []


def call(method, url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def check(name, ok, evidence):
    results.append((name, bool(ok), evidence))


def login(user):
    status, _, body = call("POST", f"{API}/auth/login", {"username": user, "password": DEMO[user]})
    assert status == 200, (user, status)
    return {"Authorization": "Bearer " + json.loads(body)["token"]}


def code(body):
    try:
        return json.loads(body)["error"]["code"]
    except Exception:
        return "?"


# 1. Güvenlik başlıkları (sayfa ve API)
s, h, _ = call("GET", WEB + "/")
h = {k.lower(): v for k, v in h.items()}
check("Sayfa: CSP frame-ancestors 'none'", "frame-ancestors 'none'" in h.get("content-security-policy", ""), h.get("content-security-policy", "")[:60] + "…")
check("Sayfa: X-Frame-Options DENY", h.get("x-frame-options") == "DENY", h.get("x-frame-options"))
check("Sayfa: nosniff", h.get("x-content-type-options") == "nosniff", h.get("x-content-type-options"))
check("Sayfa: sunucu sürümü gizli", h.get("server") == "nginx", h.get("server"))
s, h, _ = call("GET", f"{API}/health")
h = {k.lower(): v for k, v in h.items()}
check("API: Cache-Control no-store", h.get("cache-control") == "no-store", h.get("cache-control"))
check("API: X-Frame-Options DENY", h.get("x-frame-options") == "DENY", h.get("x-frame-options"))

# 2. CORS: başka siteden okuma izni yok
s, h, _ = call("OPTIONS", f"{API}/auth/login", headers={"Origin": "https://kotu.example", "Access-Control-Request-Method": "POST"})
check("CORS: kötü kökene izin yok", "access-control-allow-origin" not in {k.lower() for k in h}, f"HTTP {s}, ACAO başlığı yok")

# 3. Kimlik doğrulama
for path in ("/users", "/stock", "/audit", "/reports/sales", "/sync/pull"):
    s, _, b = call("GET", API + path)
    check(f"Girişsiz {path} → 401", s == 401, f"HTTP {s} {code(b)}")
s, _, b = call("GET", f"{API}/auth/me", headers={"Authorization": "Bearer uydurma-belirtec-123"})
check("Sahte belirteç → 401", s == 401, f"HTTP {s} {code(b)}")

# 4. Yetki (rol dışı iş)
depo = login("depo1")
store = login("magaza1")
seller = login("satis1")
for who, hdr, method, path, body in (
    ("depo1", depo, "GET", "/users", None),
    ("depo1", depo, "POST", "/recalls", {"lot_no": "ET-2026-001", "reason": "deneme"}),
    ("magaza1", store, "GET", "/audit", None),
    ("magaza1", store, "POST", "/users", {"username": "x", "full_name": "x", "role": "YONETICI", "password": "abc12345"}),
    ("satis1 (telefon)", seller, "GET", "/lots", None),
    ("satis1 (telefon)", seller, "GET", "/reports/sales", None),
):
    s, _, b = call(method, API + path, body, depo if hdr is depo else hdr)
    check(f"{who} {method} {path} → 403", s == 403 and code(b) == "FORBIDDEN", f"HTTP {s} {code(b)}")

# 5. SQL enjeksiyonu: düz metin olarak işlenir
admin = login("yonetici")
s, _, b = call("GET", f"{API}/lots?q=%27%20OR%20%271%27%3D%271", headers=admin)
check("SQLi lots?q=' OR '1'='1 → boş liste", s == 200 and json.loads(b) == [], f"HTTP {s}, {len(json.loads(b)) if s == 200 else '?'} kayıt")
s, _, b = call("GET", f"{API}/trace/forward/%27%20OR%201%3D1%20--", headers=admin)
check("SQLi trace/forward/' OR 1=1 -- → 404", s == 404, f"HTTP {s} {code(b)}")

# 6. Girdi doğrulama (veri değişmez)
s, _, b = call("POST", f"{API}/adjustments", {"lot_no": "ET-2026-001", "qty": "-999999", "reason": ""}, admin)
check("Geçersiz düzeltme → 422", s == 422, f"HTTP {s} {code(b)}")
s, _, b = call("POST", f"{API}/recalls", {"lot_no": "ET-2026-001", "reason": "x" * 501}, admin)
check("501 karakterlik neden → 422", s == 422, f"HTTP {s} {code(b)}")

# 7. Açık posta rölesi yok
s, _, b = call("POST", f"{API}/mail", {"recipients": ["saldirgan@kotu.example"], "subject": "x", "body": "x"}, depo)
check("Kayıtsız alıcıya e-posta → 422", s == 422, f"HTTP {s} {code(b)}")
s, _, b = call("POST", f"{API}/mail", {"recipients": ["a@synera.example\r\nBcc: saldirgan@kotu.example"], "subject": "x", "body": "x"}, depo)
check("Alıcıya başlık enjeksiyonu → 422", s == 422, f"HTTP {s} {code(b)}")

# 8. Büyük gövde: nginx 1 MB sınırı
s, _, _ = call("POST", f"{API}/auth/login", {"username": "x" * 2_000_000, "password": "x"})
check("2 MB gövde → 413", s == 413, f"HTTP {s}")

# 9. Kaba kuvvet: X-Real-IP sahteciliği sınırı aşamaz (en sonda; adres 5 dk kilitlenir)
statuses = []
attacker = "saldirgan_" + secrets.token_hex(3)  # her çalıştırmada yeni ad
for i in range(12):
    s, _, b = call("POST", f"{API}/auth/login", {"username": attacker, "password": f"yanlis{i}"}, {"X-Real-IP": f"10.9.9.{i}", "X-Forwarded-For": f"10.8.8.{i}"})
    statuses.append(s)
check("Kaba kuvvet: 10 denemeden sonra 429 (sahte IP başlıklarıyla)", statuses[:10] == [401] * 10 and statuses[10:] == [429, 429], " ".join(map(str, statuses)))

width = max(len(n) for n, _, _ in results)
for name, ok, evidence in results:
    print(f"{'GEÇTİ ' if ok else 'KALDI '} {name.ljust(width)}  {evidence}")
print(f"\n{sum(ok for _, ok, _ in results)}/{len(results)} geçti")
sys.exit(0 if all(ok for _, ok, _ in results) else 1)
