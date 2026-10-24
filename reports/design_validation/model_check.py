"""Mimari tasarım doğrulaması (ürün kodu değil).

Önerilen veri modelinin sade bir kopyasını bellek içi SQLite'ta kurar ve şartname
senaryolarını çalıştırır: AT-01 (EKP), AT-03 (dağıtım), AT-06/07 (izleme),
AT-08 (bloke), AT-10 (defter değişmezleri), AT-11 (çift satış).
"""
import sqlite3
from decimal import Decimal as D, ROUND_HALF_UP

CENT = D("0.01")


def r2(x):
    return x.quantize(CENT, ROUND_HALF_UP)


SCHEMA = """
create table lots(id integer primary key, lot_no text unique not null, product text not null,
  origin text not null, supplier text, status text not null default 'AKTIF',
  rem_qty text not null default '0', rem_value text not null default '0');
create table lot_links(parent_id int not null references lots(id), child_id int not null references lots(id),
  qty text not null, process text not null);
create table movements(id integer primary key, type text not null, lot_id int not null references lots(id),
  wh text not null, qty text not null, value text not null, doc text);
create table balances(lot_id int not null, wh text not null, qty text not null, primary key(lot_id, wh));
create table sales(id integer primary key, client_uuid text unique not null, customer text not null,
  recall_violation int not null default 0);
create table sale_lines(id integer primary key, sale_id int not null, lot_id int not null, qty text not null,
  movement_id int unique not null, cost text not null);
create trigger mv_no_update before update on movements begin select raise(abort, 'defter degistirilemez'); end;
create trigger mv_no_delete before delete on movements begin select raise(abort, 'defter silinemez'); end;
"""


class DomainError(Exception):
    pass


def lot(c, lot_no):
    return c.execute("select id, rem_qty, rem_value, status from lots where lot_no=?", (lot_no,)).fetchone()


def balance(c, lot_id, wh):
    row = c.execute("select qty from balances where lot_id=? and wh=?", (lot_id, wh)).fetchone()
    return D(row[0]) if row else D(0)


def post(c, mtype, lot_no, wh, qty, value=None, doc=None, transfer=False):
    """Deftere yazmanın TEK yolu. qty işaretli; value None ise değerleme kuralı uygulanır."""
    lot_id, rem_qty, rem_value, status = lot(c, lot_no)
    rem_qty, rem_value = D(rem_qty), D(rem_value)
    if qty < 0 and balance(c, lot_id, wh) + qty < 0:
        raise DomainError(f"yetersiz stok {lot_no}@{wh}")
    if transfer:
        value = D(0)  # transfer lot değerini değiştirmez
    elif value is None:  # değerli çıkış: son çıkış kalanın tamamını alır
        value = -rem_value if rem_qty + qty == 0 else -r2(rem_value * (-qty) / rem_qty)
    cur = c.execute("insert into movements(type, lot_id, wh, qty, value, doc) values(?,?,?,?,?,?)",
                    (mtype, lot_id, wh, str(qty), str(value), doc))
    c.execute("insert into balances values(?,?,?) on conflict(lot_id, wh) do update set qty=?",
              (lot_id, wh, str(qty), str(balance(c, lot_id, wh) + qty)))
    c.execute("update lots set rem_qty=?, rem_value=? where id=?", (str(rem_qty + qty), str(rem_value + value), lot_id))
    return cur.lastrowid, value


def new_lot(c, lot_no, product, origin, supplier=None):
    c.execute("insert into lots(lot_no, product, origin, supplier) values(?,?,?,?)", (lot_no, product, origin, supplier))


def link(c, parent, child, qty, process):
    c.execute("insert into lot_links values(?,?,?,?)", (lot(c, parent)[0], lot(c, child)[0], str(qty), process))


def allocate(total, weights, order):
    """En büyük kalan yöntemi; eşitlikte reçete sırası (order)."""
    s = sum(weights.values())
    raw = {k: total * w / s for k, w in weights.items()}
    floor = {k: (v / CENT).to_integral_value(rounding="ROUND_FLOOR") * CENT for k, v in raw.items()}
    missing = int((total - sum(floor.values())) / CENT)
    for k in sorted(raw, key=lambda k: (-(raw[k] - floor[k]), order.index(k)))[:missing]:
        floor[k] += CENT
    return floor


def sell(c, uuid, customer, wh, lot_no, qty):
    if c.execute("select 1 from sales where client_uuid=?", (uuid,)).fetchone():
        return "DUPLICATE"
    status = lot(c, lot_no)[3]
    sid = c.execute("insert into sales(client_uuid, customer, recall_violation) values(?,?,?)",
                    (uuid, customer, int(status == "BLOKE"))).lastrowid
    mid, value = post(c, "SATIS", lot_no, wh, -qty, doc=f"satis:{sid}")
    c.execute("insert into sale_lines(sale_id, lot_id, qty, movement_id, cost) values(?,?,?,?,?)",
              (sid, lot(c, lot_no)[0], str(qty), mid, str(-value)))
    return "ACCEPTED_WITH_WARNING" if status == "BLOKE" else "ACCEPTED"


def trace(c, lot_no, forward=True):
    """Katman katman gezinme; ziyaret kümesi döngüye karşı korur."""
    a, b = ("parent_id", "child_id") if forward else ("child_id", "parent_id")
    start = lot(c, lot_no)[0]
    seen, frontier = {start}, [start]
    while frontier:
        q = f"select {b} from lot_links where {a} in ({','.join('?' * len(frontier))})"
        frontier = [r[0] for r in c.execute(q, frontier) if r[0] not in seen]
        seen.update(frontier)
    return seen


def main():
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA)
    ok = []

    def check(name, cond, detail=""):
        ok.append(cond)
        print(("GECTI " if cond else "KALDI ") + name + (f"  [{detail}]" if detail else ""))

    # --- Görev 1: alış, sevk, dış üretim, kabul
    for lot_no, prod, sup, qty, price in [("ET-2026-001", "ET", "Tedarikci-Et", 100, "9.70"),
                                          ("BAH-2026-014", "BAHARAT", "Tedarikci-Baharat", 2, "24.00"),
                                          ("BAG-2026-007", "BAGIRSAK", "Tedarikci-Bagirsak", 5, "11.60")]:
        new_lot(c, lot_no, prod, "ALIS", sup)
        post(c, "ALIS_GIRIS", lot_no, "ANA", D(qty), value=r2(D(qty) * D(price)))
        post(c, "TRANSFER_CIKIS", lot_no, "ANA", -D(qty), transfer=True)
        post(c, "TRANSFER_GIRIS", lot_no, "DIS-URETICI", D(qty), transfer=True)
    new_lot(c, "SUC-2026-045", "NARIN_SUCUK", "URETIM")
    consumed = D(0)
    for lot_no, qty in [("ET-2026-001", 100), ("BAH-2026-014", 2), ("BAG-2026-007", 5)]:
        _, v = post(c, "URETIM_TUKETIM", lot_no, "DIS-URETICI", -D(qty), doc="URT-2026-045")
        consumed += -v
        link(c, lot_no, "SUC-2026-045", D(qty), "URETIM")
    service = r2(D(85) * D("5.50"))
    post(c, "URETIM_GIRIS", "SUC-2026-045", "ANA", D(85), value=consumed + service, doc="URT-2026-045")
    total = D(lot(c, "SUC-2026-045")[2])
    check("AT-01 toplam maliyet 1543.50", total == D("1543.50"), str(total))
    check("AT-01 EKP gosterimi 18.16", r2(total / 85) == D("18.16"), str(total / 85))
    check("AT-01 lot degeri 18.16x85 degil", total != r2(total / 85) * 85, f"{r2(total / 85) * 85} != {total}")

    # --- Araç deposuna yükleme ve Market A/B/C satışları
    post(c, "TRANSFER_CIKIS", "SUC-2026-045", "ANA", -D(85), transfer=True)
    post(c, "TRANSFER_GIRIS", "SUC-2026-045", "ARAC-01", D(85), transfer=True)
    for uuid, cust, qty in [("u-a", "Market A", 30), ("u-b", "Market B", 25), ("u-c", "Market C", 30)]:
        sell(c, uuid, cust, "ARAC-01", "SUC-2026-045", D(qty))
    check("AT-11 ayni satis ikinci kez gelirse yeni kayit yok",
          sell(c, "u-a", "Market A", "ARAC-01", "SUC-2026-045", D(30)) == "DUPLICATE")
    costs = [D(r[0]) for r in c.execute("select cost from sale_lines order by id")]
    check("Satis maliyetleri toplami = lot degeri (kurus kaymasi yok)", sum(costs) == total, " + ".join(map(str, costs)))

    # --- AT-06 ileri izleme
    lots_fwd = trace(c, "ET-2026-001")
    names = {r[0] for r in c.execute(f"select lot_no from lots where id in ({','.join('?' * len(lots_fwd))})", list(lots_fwd))}
    rows = c.execute(f"""select s.customer, sum(cast(l.qty as real)) from sale_lines l join sales s on s.id=l.sale_id
                         where l.lot_id in ({','.join('?' * len(lots_fwd))}) group by s.customer order by 1""",
                     list(lots_fwd)).fetchall()
    stock_left = sum(balance(c, lot(c, "SUC-2026-045")[0], w) for w in ("ANA", "ARAC-01", "DIS-URETICI"))
    check("AT-06 ileri izleme: SUC-2026-045 bulundu", "SUC-2026-045" in names, ", ".join(sorted(names)))
    check("AT-06 alicilar A30 / B25 / C30", rows == [("Market A", 30.0), ("Market B", 25.0), ("Market C", 30.0)], str(rows))
    check("AT-06 depoda kalan 0", stock_left == 0, str(stock_left))

    # --- AT-07 geri izleme
    back = trace(c, "SUC-2026-045", forward=False)
    srcs = sorted(c.execute(f"select lot_no, supplier from lots where origin='ALIS' and id in ({','.join('?' * len(back))})",
                            list(back)).fetchall())
    check("AT-07 geri izleme: et, baharat, bagirsak lotlari ve tedarikcileri", len(srcs) == 3, str(srcs))

    # --- AT-08 geri çağırma: bloke + sunucu satışı reddeder / çevrimdışı ihlal kaydı
    for lid in lots_fwd:
        c.execute("update lots set status='BLOKE' where id=?", (lid,))
    check("AT-08 SUC-2026-045 bloke", lot(c, "SUC-2026-045")[3] == "BLOKE")

    # --- Görev 2: parçalama dağıtımı (AT-03) ve ağırlık dengesi (AT-04)
    order = ["but", "sirt", "omuz", "kaburga", "kiyma"]
    kg = {"but": D(7), "sirt": D(4), "omuz": D(5), "kaburga": D(3), "kiyma": D(3)}
    price = {"but": D(22), "sirt": D(26), "omuz": D(18), "kaburga": D(14), "kiyma": D(16)}
    m = allocate(D("351.00"), kg, order)
    v = allocate(D("351.00"), {k: kg[k] * price[k] for k in kg}, order)
    check("AT-03 miktar agirlikli", [m[k] for k in order] == [D(x) for x in ("111.68", "63.82", "79.77", "47.87", "47.86")],
          str([str(m[k]) for k in order]))
    check("AT-03 deger agirlikli", [v[k] for k in order] == [D(x) for x in ("123.41", "83.34", "72.12", "33.66", "38.47")],
          str([str(v[k]) for k in order]))
    check("AT-03 iki yontemde toplam 351.00", sum(m.values()) == sum(v.values()) == D("351.00"))
    imbalance = D(25) - sum(kg.values())
    check("AT-04 fire girilmeden denge yok (3 kg)", imbalance == D(3), str(imbalance))

    # parçalamayı deftere işle: giriş lotu tüketilir, parça lotları dağıtılan maliyetle girer
    new_lot(c, "KUZU-2026-012", "KUZU_BUTUN", "ALIS", "Tedarikci-Kuzu")
    post(c, "ALIS_GIRIS", "KUZU-2026-012", "ANA", D(25), value=D("351.00"))
    post(c, "PARCALAMA_TUKETIM", "KUZU-2026-012", "ANA", -D(25), doc="PRC-2026-012")
    for k in order:
        new_lot(c, f"{k.upper()}-PRC-2026-012", k, "PARCALAMA")
        post(c, "PARCALAMA_GIRIS", f"{k.upper()}-PRC-2026-012", "ANA", kg[k], value=v[k], doc="PRC-2026-012")
        link(c, "KUZU-2026-012", f"{k.upper()}-PRC-2026-012", kg[k], "PARCALAMA")
    check("Parcalama: kuzu lotundan 5 parca lotuna ileri izleme", len(trace(c, "KUZU-2026-012")) == 6)

    # --- AT-10 defter değişmezleri
    inv = c.execute("""select l.lot_no, l.rem_qty, l.rem_value, coalesce(sum(cast(m.qty as real)),0), m.lot_id
                       from lots l left join movements m on m.lot_id=l.id group by l.id""").fetchall()
    qty_ok = all(abs(D(r[1]) - D(str(r[3]))) < D("0.0005") for r in inv)
    val_ok = all(D(r[2]) == sum((D(x[0]) for x in c.execute("select value from movements where lot_id=?", (r[4],))), D(0))
                 for r in inv if r[4])
    zero_ok = all(D(r[2]) == 0 for r in inv if D(r[1]) == 0)
    check("AT-10 lot miktari = hareket toplami", qty_ok)
    check("AT-10 lot degeri = hareket degeri toplami", val_ok)
    check("AT-10 miktari 0 olan lotun degeri de 0", zero_ok)
    try:
        c.execute("update movements set qty='0' where id=1")
        check("AT-10 hareket guncellenemez", False)
    except sqlite3.DatabaseError as e:
        check("AT-10 hareket guncellenemez", True, str(e))
    try:
        post(c, "SATIS", "BUT-PRC-2026-012", "ANA", -D(8))
        check("AT-10 eksi stok reddedilir", False)
    except DomainError as e:
        check("AT-10 eksi stok reddedilir", True, str(e))

    print(f"\nSONUC: {sum(ok)}/{len(ok)} kontrol gecti")


if __name__ == "__main__":
    main()
