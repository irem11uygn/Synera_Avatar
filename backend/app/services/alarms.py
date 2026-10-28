"""Alarm merkezi ve kural motoru.

İki tür alarm var:
- Olay alarmı: iş anında açılır — geri çağırma başlatıldı, bloke lot satılmak istendi, geri çağrılmış
  ya da SKT'si geçmiş parti çevrimdışı satıldı, art arda hatalı giriş.
- Kural alarmı: kural motoru kayıtları tarar (girişte, kayıt sonrası ve yöneticinin "şimdi çalıştır"
  düğmesiyle). Her durum için tek alarm açılır (rule_key); kural yeniden çalışınca tekrar etmez.

Kurallar:
- Verim sapması: z = (gerçek − model beklentisi) / σ. σ, modelin test hatasından (MAE × √(π/2),
  hatalar normal dağılımlıysa standart sapma) gelir. Tahmini olmayan emirde aynı mamulün en az
  MIN_HISTORY tamamlanmış emri varsa klasik z-skoru (ortalama ve standart sapmaya göre) kullanılır.
  Parçalamada fire kg'ı Model B'nin fire tahminiyle aynı yolla karşılaştırılır.
- Alış fiyatı artışı: aynı ürünün bir önceki alışına göre artış eşikten fazlaysa.
- Bloke lotta stok: geri çağrılmış lotta hâlâ stok varsa (imha ya da serbest bırakma kararı bekliyor).

- Son kullanma: elimizdeki (ana depo, araç) lotun SKT'si 3 gün içinde ya da geçmiş.

Alarm e-postası abonelere gider (services/subscriptions.py: yönetici bütün türlere, diğer roller kendi
işini ilgilendiren türlere); her alıcıya ayrı e-posta, aynı alarm aynı adrese bir kez (dedup_key).
Alarm aynı zamanda denetim günlüğüne yazılır.
"""

import html
import logging
import math
import statistics
from dataclasses import dataclass, field
from datetime import UTC, timedelta
from decimal import Decimal
from urllib.parse import quote

from avatar_ml import predict
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app import mailer
from app.config import get_settings
from app.domain.clock import business_today, business_zone
from app.domain.money import round_percent, tr_number
from app.errors import Forbidden, InvalidInput
from app.models import (
    AiForecast,
    Alert,
    AuditEvent,
    Cutting,
    CuttingOutput,
    Lot,
    Partner,
    Product,
    ProductionOrder,
    Purchase,
    PurchaseLine,
    Recall,
    RecallLot,
    Sale,
    SaleLine,
    StockBalance,
    StockCount,
    User,
    Warehouse,
)
from app.models.enums import (
    AlertKind,
    BaseUnit,
    CuttingStatus,
    ForecastTarget,
    LotStatus,
    ProductionStatus,
    RecallStatus,
    RecipeLineType,
    Severity,
    UserRole,
    WarehouseKind,
)
from app.models.types import utcnow
from app.services import app_settings, audit, mail, subscriptions
from app.services.app_settings import Thresholds
from app.services.production import order_summary
from app.services.subscriptions import visible_kinds

logger = logging.getLogger(__name__)

SQRT_HALF_PI = Decimal(str(math.sqrt(math.pi / 2)))  # normal dağılımda σ = MAE × √(π/2)
MIN_HISTORY = 5
PRICE_LOOKBACK = timedelta(days=365)

KIND_LABEL = {
    AlertKind.GERI_CAGIRMA_IHLALI: "Geri çağrılmış ürün satıldı",
    AlertKind.SKT_IHLALI: "SKT'si geçmiş ürün satıldı",
    AlertKind.GERI_CAGIRMA: "Geri çağırma başlatıldı",
    AlertKind.BLOKE_SATIS_DENEMESI: "Bloke lot satış denemesi",
    AlertKind.BLOKE_STOK: "Bloke lotta stok var",
    AlertKind.VERIM_SAPMASI: "Verim sapması",
    AlertKind.FIYAT_ARTISI: "Alış fiyatı artışı",
    AlertKind.HATALI_GIRIS: "Art arda hatalı giriş",
    AlertKind.SKT_YAKLASIYOR: "Son kullanma tarihi yaklaşan lot",
    AlertKind.SAYIM_FARKI: "Sayım farkı",
}
SEVERITY_LABEL = {Severity.BILGI: "Bilgi", Severity.UYARI: "Uyarı", Severity.KRITIK: "Kritik"}

R = UserRole
_ACK_DEFAULT = frozenset({R.YONETICI, R.KALITE})
ACK_ROLES = {
    AlertKind.VERIM_SAPMASI: frozenset({R.YONETICI, R.KALITE, R.URETIM}),
    AlertKind.FIYAT_ARTISI: frozenset({R.YONETICI, R.DEPO}),
    AlertKind.BLOKE_STOK: frozenset({R.YONETICI, R.KALITE, R.DEPO}),
    AlertKind.BLOKE_SATIS_DENEMESI: frozenset({R.YONETICI, R.KALITE, R.MAGAZA}),
    AlertKind.HATALI_GIRIS: frozenset({R.YONETICI}),
    AlertKind.SKT_YAKLASIYOR: frozenset({R.YONETICI, R.KALITE, R.DEPO, R.MAGAZA}),
    AlertKind.SAYIM_FARKI: frozenset({R.YONETICI, R.DEPO}),
}
EXPIRY_WARNING_DAYS = 3  # ana sayfadaki "dolmak üzere" süresiyle aynı
OWN_STOCK = (WarehouseKind.ANA, WarehouseKind.ARAC)


def can_acknowledge(user: User, alert: Alert) -> bool:
    return user.role in ACK_ROLES.get(alert.kind, _ACK_DEFAULT)


def raise_alarm(
    session: Session,
    kind: AlertKind,
    severity: Severity,
    message: str,
    *,
    ref_type: str,
    ref_id: int,
    rule_key: str | None = None,
    user: User | None = None,
) -> Alert | None:
    """Alarmı açar, denetim günlüğüne yazar, abonelere e-postasını kuyruğa koyar. Aynı rule_key varsa None."""
    if rule_key and session.scalar(select(Alert.id).where(Alert.rule_key == rule_key)) is not None:
        return None
    alert = Alert(
        kind=kind,
        severity=severity,
        ref_type=ref_type,
        ref_id=ref_id,
        message=message[:500],
        rule_key=rule_key,
    )
    try:
        with session.begin_nested():  # aynı anda iki kural çalışması: ikincisi sessizce vazgeçer
            session.add(alert)
            session.flush()
    except IntegrityError:
        return None
    audit.log(
        session,
        "ALARM",
        f"{KIND_LABEL[kind]}: {message}",
        user=user,
        severity=severity,
        ref_type="ALERT",
        ref_id=alert.id,
    )
    notify(session, alert)
    return alert


def notify(session: Session, alert: Alert) -> list[str]:
    """Abonelere e-posta: her alıcıya ayrı (birbirini görmez); aynı alarm aynı adrese bir kez gider."""
    subject, html_body, text = alert_mail(session, alert)
    queued: list[str] = []
    for subscriber in subscriptions.subscribers(session, alert.kind):
        email = (subscriber.email or "").strip()
        try:
            message = mail.queue(
                session,
                recipients=[email],
                subject=subject,
                body=text,
                html=html_body,
                kind="ALARM",
                alert_id=alert.id,
                dedup_key=f"ALERT:{alert.id}:{email.lower()}"[:150],
            )
        except InvalidInput:  # kayıtlı adres bozuksa iş durmaz; günlüğe yazılır
            logger.warning(
                "Alarm e-postası kuyruğa alınamadı: geçersiz adres %r (kullanıcı %s)", email, subscriber.id
            )
            continue
        if message is not None:
            queued.append(email)
    return queued


def alert_mail(session: Session, alert: Alert) -> tuple[str, str, str]:
    """Konu, HTML ve düz metin. Konu: [AVATAR UYARI] <başlık>; gövde: özet, lot/ürün, bağlantı."""
    title = KIND_LABEL[alert.kind]
    when = alert.created_at.replace(tzinfo=UTC).astimezone(business_zone())
    rows = [
        ("Önem", SEVERITY_LABEL[alert.severity]),
        ("Zaman", f"{when:%d.%m.%Y %H:%M}"),
        ("Alarm no", str(alert.id)),
        *_alert_context(session, alert),
    ]
    base = get_settings().web_base_url
    path, link_label = _alert_link(session, alert)
    esc = html.escape
    table = mailer.html_rows(rows)
    html_body = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;color:#102a2a;max-width:640px">'
        '<div style="background:#0d9488;color:#ffffff;padding:14px 18px;border-radius:10px 10px 0 0">'
        "<strong>AVATAR · Synera uyarısı</strong></div>"
        '<div style="border:1px solid #dbe7e5;border-top:0;padding:18px;border-radius:0 0 10px 10px">'
        f'<h2 style="margin:0 0 8px;font-size:18px">{esc(title)}</h2>'
        f'<p style="margin:0 0 14px">{esc(alert.message)}</p>'
        f'<table style="border-collapse:collapse;font-size:14px">{table}</table>'
        f'<p style="margin:18px 0 6px"><a href="{esc(base + path)}" style="background:#0d9488;color:#ffffff;'
        f'padding:10px 16px;border-radius:8px;text-decoration:none">{esc(link_label)}</a></p>'
        '<p style="font-size:13px;color:#5f7372">'
        f'Alarm merkezi: <a href="{esc(base)}/alarmlar">{esc(base)}/alarmlar</a></p>'
        "</div></div>"
    )
    text = "\n".join(
        [
            title,
            "",
            alert.message,
            "",
            *(f"{k}: {v}" for k, v in rows),
            "",
            f"{link_label}: {base}{path}",
            f"Alarm merkezi: {base}/alarmlar",
        ]
    )
    return f"[AVATAR UYARI] {title}", html_body, text


def _unit(product: Product | None) -> str:
    return "adet" if product is not None and product.base_unit == BaseUnit.ADET else "kg"


def _alert_context(session: Session, alert: Alert) -> list[tuple[str, str]]:
    """Uyarının ilgili olduğu lot, ürün ve belge bilgisi (e-postada tablo)."""
    ref, ref_id = alert.ref_type, alert.ref_id
    if ref == "LOT" and (lot := session.get(Lot, ref_id)):
        product = session.get(Product, lot.product_id)
        rows = [
            ("Lot", lot.lot_no),
            ("Ürün", product.name if product else "?"),
            ("Kalan", f"{tr_number(lot.remaining_qty)} {_unit(product)}"),
        ]
        if lot.expiry_date:
            rows.append(("Son kullanma", f"{lot.expiry_date:%d.%m.%Y}"))
        return rows
    if ref == "RECALL" and (recall := session.get(Recall, ref_id)):
        lot = session.get(Lot, recall.source_lot_id)
        product = session.get(Product, lot.product_id) if lot else None
        return [
            ("Geri çağırma", recall.recall_no),
            ("Kaynak lot", lot.lot_no if lot else "?"),
            ("Ürün", product.name if product else "?"),
        ]
    if ref == "SALE" and (sale := session.get(Sale, ref_id)):
        customer = session.get(Partner, sale.customer_id)
        lots = session.execute(
            select(Lot.lot_no, Product.name)
            .join(SaleLine, SaleLine.lot_id == Lot.id)
            .join(Product, Product.id == SaleLine.product_id)
            .where(SaleLine.sale_id == sale.id)
        ).all()
        return [
            ("Satış", sale.sale_no),
            ("Müşteri", customer.name if customer else "?"),
            ("Lot / ürün", ", ".join(f"{no} — {name}" for no, name in lots)),
        ]
    if ref == "PRODUCTION_ORDER" and (order := session.get(ProductionOrder, ref_id)):
        product = session.get(Product, order.output_product_id)
        lot = session.get(Lot, order.output_lot_id) if order.output_lot_id else None
        return [
            ("Üretim emri", order.order_no),
            ("Mamul", product.name if product else "?"),
            ("Mamul lotu", lot.lot_no if lot else "—"),
        ]
    if ref == "CUTTING" and (cutting := session.get(Cutting, ref_id)):
        lot = session.get(Lot, cutting.input_lot_id)
        product = session.get(Product, lot.product_id) if lot else None
        return [
            ("Parçalama", cutting.cutting_no),
            ("Giriş lotu", lot.lot_no if lot else "?"),
            ("Ürün", product.name if product else "?"),
        ]
    if ref == "PURCHASE" and (purchase := session.get(Purchase, ref_id)):
        supplier = session.get(Partner, purchase.supplier_id)
        lots = session.execute(
            select(Lot.lot_no, Product.name)
            .join(PurchaseLine, PurchaseLine.lot_id == Lot.id)
            .join(Product, Product.id == PurchaseLine.product_id)
            .where(PurchaseLine.purchase_id == purchase.id)
        ).all()
        return [
            ("Belge", purchase.doc_no),
            ("Tedarikçi", supplier.name if supplier else "?"),
            ("Lot / ürün", ", ".join(f"{no} — {name}" for no, name in lots)),
        ]
    if ref == "STOCK_COUNT" and (count := session.get(StockCount, ref_id)):
        warehouse = session.get(Warehouse, count.warehouse_id)
        return [
            ("Sayım", count.count_no),
            ("Depo", f"{warehouse.code} — {warehouse.name}" if warehouse else "?"),
        ]
    if ref == "USER" and (account := session.get(User, ref_id)):
        return [("Hesap", account.username)]
    return []


def _alert_link(session: Session, alert: Alert) -> tuple[str, str]:
    ref, ref_id = alert.ref_type, alert.ref_id
    if ref == "LOT" and (lot := session.get(Lot, ref_id)):
        return f"/lotlar/{quote(lot.lot_no)}", "Lot kartını aç"
    return {
        "RECALL": (f"/geri-cagirma/{ref_id}", "Geri çağırmayı aç"),
        "SALE": ("/satislar", "Satışları aç"),
        "PRODUCTION_ORDER": (f"/uretim/{ref_id}", "Üretim emrini aç"),
        "CUTTING": (f"/parcalama/{ref_id}", "Parçalamayı aç"),
        "PURCHASE": ("/alislar", "Mal kabulü aç"),
        "STOCK_COUNT": ("/sayim", "Sayımları aç"),
    }.get(ref, ("/alarmlar", "Alarm merkezini aç"))


def acknowledge(session: Session, user: User, alert: Alert) -> Alert:
    if not can_acknowledge(user, alert) or alert.kind not in visible_kinds(user):
        raise Forbidden("Bu alarmı okundu işaretleme yetkiniz yok.", role=user.role)
    if alert.acknowledged_at is None:
        alert.acknowledged_at = utcnow()
        alert.acknowledged_by = user.id
        audit.log(
            session,
            "ALARM_OKUNDU",
            f"{KIND_LABEL[alert.kind]} alarmı okundu işaretlendi: {alert.message}",
            user=user,
            ref_type="ALERT",
            ref_id=alert.id,
        )
        session.flush()
    return alert


# ---------------------------------------------------------------------------- olay alarmları


def recall_started(session: Session, recall: Recall, user: User | None, lot_no: str, lot_count: int) -> None:
    raise_alarm(
        session,
        AlertKind.GERI_CAGIRMA,
        Severity.KRITIK,
        f"{recall.recall_no} başlatıldı: {lot_no} ve ondan üretilen {lot_count} lot bloke edildi. "
        f"Neden: {recall.reason}",
        ref_type="RECALL",
        ref_id=recall.id,
        user=user,
    )


def stock_count_difference(
    session: Session,
    user: User,
    *,
    count_id: int,
    count_no: str,
    warehouse_code: str,
    differences: list[tuple[str, str, str, Decimal]],
    shortage_value: Decimal,
) -> None:
    """Sayımda sistemle sayılan farklıysa: (lot, ürün, birim, fark) listesiyle uyarı."""
    if not differences:
        return
    shown = "; ".join(
        f"{lot_no} {name}: {'+' if d > 0 else ''}{tr_number(d)} {unit}"
        for lot_no, name, unit, d in differences[:6]
    )
    more = f" ve {len(differences) - 6} lot daha" if len(differences) > 6 else ""
    raise_alarm(
        session,
        AlertKind.SAYIM_FARKI,
        Severity.UYARI,
        f"{count_no} ({warehouse_code}) sayımında {len(differences)} lotta fark: {shown}{more}. "
        f"Eksik değeri {tr_number(shortage_value, 2)} €. Eksik fire olarak düşüldü; "
        "fazlanın kaynağını araştırın.",
        ref_type="STOCK_COUNT",
        ref_id=count_id,
        user=user,
    )


def blocked_sale_attempt(session: Session, user: User, lot_no: str) -> None:
    lot = session.scalars(select(Lot).where(Lot.lot_no == lot_no)).first()
    raise_alarm(
        session,
        AlertKind.BLOKE_SATIS_DENEMESI,
        Severity.KRITIK,
        f"{user.full_name} ({user.username}) bloke {lot_no} lotunu mağazada satmak istedi; "
        "satış engellendi. Ürün rafta ise ayırın.",
        ref_type="LOT",
        ref_id=lot.id if lot else 0,
        user=user,
    )


def login_failed(session: Session, username: str, client: str, threshold: int | None = None) -> None:
    """Hatalı girişi günlüğe yazar; son başarılı girişten beri tam eşik kadar olduysa kritik alarm."""
    name = username.strip().lower()[:50]
    audit.log(
        session,
        "GIRIS_HATASI",
        f"Hatalı giriş denemesi: '{name}'",
        username=name,
        severity=Severity.UYARI,
        client=client,
    )
    limit = threshold or app_settings.thresholds(session).failed_logins
    last_success = session.scalar(
        select(func.max(AuditEvent.id)).where(AuditEvent.username == name, AuditEvent.action == "GIRIS")
    )
    failures = (
        session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.username == name,
                AuditEvent.action == "GIRIS_HATASI",
                AuditEvent.id > (last_success or 0),
            )
        )
        or 0
    )
    if failures == limit:
        user = session.scalars(select(User).where(User.username == name)).one_or_none()
        raise_alarm(
            session,
            AlertKind.HATALI_GIRIS,
            Severity.KRITIK,
            f"'{name}' hesabına art arda {failures} hatalı giriş denemesi (son adres: {client}). "
            + (
                "Hesap sahibine sorun; tanımadığı bir deneme ise şifresini sıfırlayın."
                if user
                else "Bu adla bir kullanıcı yok."
            ),
            ref_type="USER",
            ref_id=user.id if user else 0,
        )


# ---------------------------------------------------------------------------- kural motoru


@dataclass
class RuleRun:
    created: list[Alert] = field(default_factory=list)
    checked: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def run_rules(session: Session, user: User | None = None) -> RuleRun:
    th = app_settings.thresholds(session)
    run = RuleRun()
    rules = (
        ("verim", _yield_rules),
        ("fiyat", _price_rules),
        ("bloke", _blocked_stock_rules),
        ("skt", _expiry_rules),
    )
    for name, rule in rules:
        try:
            with session.begin_nested():
                checked, created, notes = rule(session, th, user)
        except SQLAlchemyError:
            raise  # bağlantı/işlem sorunu isteğin kendi hatasıdır, yutulmaz
        except Exception:  # bir kuralın hatası diğerlerini ve asıl işi durdurmaz
            logger.exception("Alarm kuralı çalışmadı: %s", name)
            run.notes.append(f"{name} kuralı çalışmadı (sistem günlüğüne bakın).")
            continue
        run.checked[name] = checked
        run.created.extend(created)
        run.notes.extend(notes)
    return run


def _model_sigma() -> tuple[Decimal | None, Decimal | None, str | None]:
    """Model A verim σ'sı (yüzde puan) ve Model B fire σ'sı (kg)."""
    try:
        meta = predict.metadata()
        yield_mae = Decimal(str(meta["model_a"]["test"]["model"]["yield_mae_pp"]))
        fire_mae = Decimal(str(meta["model_b"]["test"]["model"]["mae_kg_by_part"]["FIRE"]))
    except (predict.ModelUnavailable, KeyError, TypeError) as error:
        return None, None, f"Model bilgisi okunamadı ({error}); verim kuralı yalnız geçmişe göre çalıştı."
    return yield_mae * SQRT_HALF_PI, fire_mae * SQRT_HALF_PI, None


def _actual_yield_pct(session: Session, order: ProductionOrder) -> Decimal | None:
    """Et bazlı verim, emir özetindekiyle aynı hesap (mamul kg / ana hammadde kg)."""
    result = order_summary(session, order).yield_
    return result.yield_main_pct if result else None


def _yield_rules(session: Session, th: Thresholds, user: User | None) -> tuple[int, list[Alert], list[str]]:
    sigma_yield, sigma_fire, note = _model_sigma()
    notes = [note] if note else []
    created: list[Alert] = []
    orders = session.scalars(
        select(ProductionOrder).where(
            ProductionOrder.status == ProductionStatus.TAMAMLANDI, ProductionOrder.received_qty.is_not(None)
        )
    ).all()
    actual = {o.id: y for o in orders if (y := _actual_yield_pct(session, o)) is not None}
    forecasts = {
        f.target_id: Decimal(f.prediction["yield_main_pct"])
        for f in session.scalars(
            select(AiForecast).where(AiForecast.target_type == ForecastTarget.URETIM_EMRI)
        )
        if "yield_main_pct" in f.prediction
    }
    for order in orders:
        if order.id not in actual:
            continue
        value = actual[order.id]
        if order.id in forecasts and sigma_yield:
            expected, sigma, basis = forecasts[order.id], sigma_yield, "model beklentisi"
        else:
            history = [
                actual[o.id]
                for o in orders
                if o.id != order.id and o.output_product_id == order.output_product_id and o.id in actual
            ]
            if len(history) < MIN_HISTORY:
                continue
            expected = Decimal(str(statistics.fmean(history)))
            sigma = Decimal(str(statistics.stdev(history)))
            basis = f"son {len(history)} emrin ortalaması"
            if sigma == 0:
                continue
        z = (value - expected) / sigma
        if abs(z) <= th.yield_z:
            continue
        direction = "düşük" if z < 0 else "yüksek"
        alert = raise_alarm(
            session,
            AlertKind.VERIM_SAPMASI,
            Severity.UYARI,
            f"{order.order_no}: et bazlı verim %{tr_number(round_percent(value))}, {basis} "
            f"%{tr_number(round_percent(expected))} — beklenenden {direction} "
            f"(z = {tr_number(round_percent(z))}, "
            f"eşik ±{tr_number(th.yield_z)}). Tartımı ve dış üreticinin teslimini kontrol edin.",
            ref_type="PRODUCTION_ORDER",
            ref_id=order.id,
            rule_key=f"VERIM:URT:{order.id}",
            user=user,
        )
        if alert:
            created.append(alert)
    cuttings = session.scalars(select(Cutting).where(Cutting.status == CuttingStatus.ONAYLANDI)).all()
    for cutting in cuttings:
        fire = session.scalars(
            select(CuttingOutput).where(
                CuttingOutput.cutting_id == cutting.id, CuttingOutput.line_type == RecipeLineType.FIRE
            )
        ).first()
        if fire is None or fire.actual_qty is None or fire.predicted_qty is None or not sigma_fire:
            continue
        z = (fire.actual_qty - fire.predicted_qty) / sigma_fire
        if abs(z) <= th.yield_z:
            continue
        alert = raise_alarm(
            session,
            AlertKind.VERIM_SAPMASI,
            Severity.UYARI,
            f"{cutting.cutting_no}: fire {tr_number(fire.actual_qty)} kg, model beklentisi "
            f"{tr_number(fire.predicted_qty)} kg (z = {tr_number(round_percent(z))}, "
            f"eşik ±{tr_number(th.yield_z)}). "
            "Tartımı ve parçalamayı kontrol edin.",
            ref_type="CUTTING",
            ref_id=cutting.id,
            rule_key=f"VERIM:PRC:{cutting.id}",
            user=user,
        )
        if alert:
            created.append(alert)
    return len(actual) + len(cuttings), created, notes


def _price_rules(session: Session, th: Thresholds, user: User | None) -> tuple[int, list[Alert], list[str]]:
    since = (utcnow() - PRICE_LOOKBACK).date()
    rows = session.execute(
        select(PurchaseLine, Purchase)
        .join(Purchase, Purchase.id == PurchaseLine.purchase_id)
        .where(Purchase.doc_date >= since)
        .order_by(PurchaseLine.product_id, Purchase.doc_date, PurchaseLine.id)
    ).all()
    created: list[Alert] = []
    previous: dict[int, tuple[PurchaseLine, Purchase]] = {}
    for line, purchase in rows:
        before = previous.get(line.product_id)
        previous[line.product_id] = (line, purchase)
        if before is None or before[0].unit_price <= 0:
            continue
        increase = (line.unit_price - before[0].unit_price) / before[0].unit_price * 100
        if increase <= th.price_increase_pct:
            continue
        product = session.get(Product, line.product_id)
        supplier = session.get(Partner, purchase.supplier_id)
        alert = raise_alarm(
            session,
            AlertKind.FIYAT_ARTISI,
            Severity.UYARI,
            f"{product.name if product else 'Ürün'}: {purchase.doc_no} "
            f"({supplier.name if supplier else '?'}) "
            f"birim fiyatı {tr_number(line.unit_price, 2)} €, önceki alış {before[1].doc_no} "
            f"{tr_number(before[0].unit_price, 2)} € — %{tr_number(round_percent(increase))} artış "
            f"(eşik %{tr_number(th.price_increase_pct)}). Faturayı ve anlaşmayı kontrol edin.",
            ref_type="PURCHASE",
            ref_id=purchase.id,
            rule_key=f"FIYAT:{line.id}",
            user=user,
        )
        if alert:
            created.append(alert)
    return len(rows), created, []


def _blocked_stock_rules(
    session: Session, th: Thresholds, user: User | None
) -> tuple[int, list[Alert], list[str]]:
    rows = session.execute(
        select(Lot, Recall)
        .join(RecallLot, RecallLot.lot_id == Lot.id)
        .join(Recall, Recall.id == RecallLot.recall_id)
        .where(Lot.status == LotStatus.BLOKE, Recall.status == RecallStatus.ACIK, Lot.remaining_qty > 0)
    ).all()
    created: list[Alert] = []
    for lot, recall in rows:
        product = session.get(Product, lot.product_id)
        unit = "adet" if product and product.base_unit == BaseUnit.ADET else "kg"
        alert = raise_alarm(
            session,
            AlertKind.BLOKE_STOK,
            Severity.UYARI,
            f"{lot.lot_no} ({product.name if product else '?'}) {recall.recall_no} ile bloke, ama elde hâlâ "
            f"{tr_number(lot.remaining_qty)} {unit} var. Ürünü ayırın; geri çağırma kapanırken imha ya da "
            "serbest bırakma kararı verilir.",
            ref_type="LOT",
            ref_id=lot.id,
            rule_key=f"BLOKE_STOK:{recall.id}:{lot.id}",
            user=user,
        )
        if alert:
            created.append(alert)
    return len(rows), created, []


def _expiry_rules(session: Session, th: Thresholds, user: User | None) -> tuple[int, list[Alert], list[str]]:
    """Elimizdeki (ana depo, araç) satışa açık lotlarda SKT 3 gün içinde ya da geçmişse."""
    today = business_today()
    rows = session.execute(
        select(Lot, Product, func.sum(StockBalance.qty), func.group_concat(Warehouse.code))
        .join(StockBalance, StockBalance.lot_id == Lot.id)
        .join(Warehouse, Warehouse.id == StockBalance.warehouse_id)
        .join(Product, Product.id == Lot.product_id)
        .where(
            Warehouse.kind.in_(OWN_STOCK),
            StockBalance.qty > 0,
            Lot.status == LotStatus.AKTIF,
            Lot.expiry_date.is_not(None),
            Lot.expiry_date <= today + timedelta(days=EXPIRY_WARNING_DAYS),
        )
        .group_by(Lot.id, Product.id)
    ).all()
    created: list[Alert] = []
    for lot, product, qty, warehouses in rows:
        days = (lot.expiry_date - today).days
        held = f"elde {tr_number(qty)} {_unit(product)} ({warehouses})"
        if days < 0:
            text = (
                f"{lot.lot_no} ({product.name}) son kullanma tarihi "
                f"{lot.expiry_date:%d.%m.%Y} geçti; {held}. "
                "Satılamaz: rafından ayırın, fire/imha kaydı girin."
            )
        else:
            when = "bugün" if days == 0 else f"{days} gün sonra"
            text = (
                f"{lot.lot_no} ({product.name}) son kullanma tarihi "
                f"{lot.expiry_date:%d.%m.%Y} ({when}); {held}. "
                "Önce bunu satın (ilk dolan ilk çıkar)."
            )
        alert = raise_alarm(
            session,
            AlertKind.SKT_YAKLASIYOR,
            Severity.UYARI,
            text,
            ref_type="LOT",
            ref_id=lot.id,
            rule_key=f"SKT:{lot.id}:{lot.expiry_date:%Y%m%d}:{'gecti' if days < 0 else 'yakin'}",
            user=user,
        )
        if alert:
            created.append(alert)
    return len(rows), created, []
