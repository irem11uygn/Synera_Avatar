"""Fatura / irsaliye metninden mal kabul önerisi.

Kural tabanlı ayrıştırıcı: metindeki tedarikçiyi, belge numarasını, tarihi ve satırları (ürün, miktar,
lot, birim fiyat, tutar, SKT) bulur. Hiçbir şey kaydetmez: öneri mal kabul formuna doldurulur, kullanıcı
kontrol edip düzeltir ve kendisi kaydeder (insan onayı). Bulunamayan ya da emin olunamayan her alan
uyarıyla bildirilir; tahmin edilmiş bir lot numarası asla uydurulmaz (izlenebilirlik tedarikçinin
etiketindeki lot numarasına dayanır).
"""

import difflib
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import InvalidInput
from app.models import Partner, Product
from app.models.enums import BaseUnit, ProductKind

MAX_TEXT = 20000
_NUMBER = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?"  # önce binlik ayraçlı yazım
_DATE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")
_EXPIRY = re.compile(
    r"(?:S\.?\s?K\.?\s?T\.?|TETT|son\s+kullanma(?:\s+tarihi)?|expiry|best\s+before)\s*[:.]?\s*"
    r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})",
    re.IGNORECASE,
)
_DOC_NO = re.compile(
    r"(?:fatura|irsaliye|belge|invoice|delivery\s+note)\s*(?:no\b\.?|numaras[ıi]|nr\b\.?|#|:)\s*[:.]?\s*"
    r"([A-Z0-9][A-Z0-9\-/]{2,49})",
    re.IGNORECASE,
)
_LOT_LABELED = re.compile(
    r"(?:lot|parti|batch|seri)\s*(?:no)?\s*[:.]?\s*([A-Z0-9][A-Z0-9\-/]{2,39})", re.IGNORECASE
)
_LOT_SHAPE = re.compile(r"\b([A-Z]{2,8}(?:-[A-Z]{1,8})?-\d{4}-\d{2,6})\b")
_QTY = re.compile(rf"({_NUMBER})\s*(kg|kilo(?:gram)?|adet|ad\.?|pkt|paket|pcs|piece)\b", re.IGNORECASE)
_PRICE = re.compile(
    rf"(?:[x×@*]\s*({_NUMBER})\s*(?:€|eur|euro)?|({_NUMBER})\s*(?:€|eur|euro)\s*/\s*(?:kg|adet|ad))",
    re.IGNORECASE,
)
_AMOUNT = re.compile(rf"(?:=|tutar|toplam|amount)\s*[:]?\s*({_NUMBER})\s*(?:€|eur|euro)?", re.IGNORECASE)
_PLAIN_EURO = re.compile(rf"({_NUMBER})\s*(?:€|eur|euro)\b", re.IGNORECASE)
_UNIT_ADET = ("adet", "ad", "ad.", "pkt", "paket", "pcs", "piece")


@dataclass
class LineSuggestion:
    source: str
    product_id: int | None
    product_code: str | None
    product_name: str | None
    match: str  # "kod" | "ad" | "benzer" | "yok"
    qty: Decimal | None
    unit: str | None
    unit_price: Decimal | None
    invoice_amount: Decimal | None
    lot_no: str | None
    expiry_date: date | None
    warnings: list[str] = field(default_factory=list)


@dataclass
class InvoiceSuggestion:
    supplier_id: int | None
    supplier_name: str | None
    doc_no: str | None
    doc_date: date | None
    lines: list[LineSuggestion]
    warnings: list[str]


def parse_number(text: str) -> Decimal | None:
    """Türkçe ve İngilizce yazım: 1.188,00 · 1188,5 · 9,90 · 9.90 · 1 188,00 · 120."""
    value = text.strip().replace(" ", "").replace(" ", "")
    if not value:
        return None
    if "," in value and "." in value:
        decimal_sep = "," if value.rfind(",") > value.rfind(".") else "."
        thousands = "." if decimal_sep == "," else ","
        value = value.replace(thousands, "").replace(decimal_sep, ".")
    elif "," in value:
        value = value.replace(",", ".")
    elif "." in value and re.fullmatch(r"\d{1,3}(\.\d{3})+", value):
        value = value.replace(".", "")  # 1.188 → bin yüz seksen sekiz
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _fold(text: str) -> str:
    table = str.maketrans("İIıŞşĞğÜüÖöÇç", "iiissgguuoocc")
    return re.sub(r"\s+", " ", text.translate(table).lower()).strip()


def _date(match: re.Match[str]) -> date | None:
    try:
        return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
    except ValueError:
        return None


def _match_product(line: str, products: list[Product]) -> tuple[Product | None, str]:
    folded = _fold(line)
    upper = line.upper()
    by_code = [p for p in products if re.search(rf"(?<![A-Z0-9-]){re.escape(p.code)}(?![A-Z0-9-])", upper)]
    if by_code:
        return max(by_code, key=lambda p: len(p.code)), "kod"
    by_name = [p for p in products if _fold(p.name) in folded]
    if by_name:
        return max(by_name, key=lambda p: len(p.name)), "ad"
    words = re.findall(r"[a-z0-9]+", folded)
    best: tuple[float, Product | None] = (0.0, None)
    for product in products:
        name_words = re.findall(r"[a-z0-9]+", _fold(product.name))
        if not name_words:
            continue
        span = len(name_words)
        for i in range(max(1, len(words) - span + 1)):
            ratio = difflib.SequenceMatcher(None, " ".join(words[i : i + span]), " ".join(name_words)).ratio()
            if ratio > best[0]:
                best = (ratio, product)
    if best[1] is not None and best[0] >= 0.8:
        return best[1], "benzer"
    return None, "yok"


def parse_invoice_text(session: Session, text: str) -> InvoiceSuggestion:
    if not text.strip():
        raise InvalidInput("Fatura ya da irsaliye metnini yapıştırın.")
    if len(text) > MAX_TEXT:
        raise InvalidInput(f"Metin en çok {MAX_TEXT} karakter olabilir.")
    products = list(
        session.scalars(
            select(Product).where(Product.active, Product.kind == ProductKind.HAMMADDE).order_by(Product.id)
        )
    )
    suppliers = list(session.scalars(select(Partner).where(Partner.is_supplier).order_by(Partner.id)))
    warnings: list[str] = []

    supplier = _find_supplier(text, suppliers)
    if supplier is None:
        warnings.append("Tedarikçi metinde bulunamadı; listeden seçin.")
    doc_no = next(
        (m.group(1).rstrip(".-/") for m in _DOC_NO.finditer(text) if re.search(r"\d", m.group(1))), None
    )
    if doc_no is None:
        warnings.append("Belge (fatura/irsaliye) numarası bulunamadı; elle yazın.")
    expiry_spans = [m.span() for m in _EXPIRY.finditer(text)]
    doc_date = None
    for match in _DATE.finditer(text):
        if any(start <= match.start() < end for start, end in expiry_spans):
            continue  # SKT belge tarihi değildir
        doc_date = _date(match)
        if doc_date:
            break
    if doc_date is None:
        warnings.append("Belge tarihi bulunamadı; elle seçin.")

    lines: list[LineSuggestion] = []
    pending_expiry: date | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        product, how = _match_product(line, products)
        expiry = _date(m) if (m := _EXPIRY.search(line)) else None
        if product is None:
            if expiry and lines and lines[-1].expiry_date is None:
                lines[-1].expiry_date = expiry  # SKT ürünün altındaki satırda yazılmış
            elif expiry:
                pending_expiry = expiry
            continue
        suggestion = _line(line, product, how, expiry or pending_expiry)
        if suggestion.qty is None and suggestion.unit_price is None:
            continue  # ürün adı geçiyor ama satır değil (ör. "TED-ET Et Ürünleri" başlığı)
        lines.append(suggestion)
        pending_expiry = None
    if not lines:
        warnings.append("Metinde tanınan bir ürün satırı yok; ürün adını ya da kodunu kontrol edin.")
    return InvoiceSuggestion(
        supplier_id=supplier.id if supplier else None,
        supplier_name=supplier.name if supplier else None,
        doc_no=doc_no,
        doc_date=doc_date,
        lines=lines,
        warnings=warnings,
    )


def _find_supplier(text: str, suppliers: list[Partner]) -> Partner | None:
    folded, upper = _fold(text), text.upper()
    hits = [
        (len(p.name), p)
        for p in suppliers
        if _fold(p.name) in folded or re.search(rf"(?<![A-Z0-9-]){re.escape(p.code)}(?![A-Z0-9-])", upper)
    ]
    return max(hits, key=lambda hit: hit[0])[1] if hits else None


def _line(line: str, product: Product, how: str, expiry: date | None) -> LineSuggestion:
    warnings: list[str] = []
    lot_no = None
    if labeled := _LOT_LABELED.search(line):
        lot_no = labeled.group(1).rstrip(".-/")
    elif shaped := _LOT_SHAPE.search(line):
        lot_no = shaped.group(1)
    if lot_no is None:
        warnings.append("Lot numarası yok: tedarikçinin etiketindeki lot numarasını yazın.")
    without_lot = line.replace(lot_no, " ") if lot_no else line
    without_dates = _DATE.sub(" ", without_lot)

    qty = unit = None
    if found := _QTY.search(without_dates):
        qty, unit = parse_number(found.group(1)), found.group(2).lower()
    expected_unit = "adet" if product.base_unit == BaseUnit.ADET else "kg"
    if unit is not None:
        unit = "adet" if unit in _UNIT_ADET else "kg"
        if unit != expected_unit:
            warnings.append(
                f"Belgede birim {unit}, ürün {expected_unit} ile izleniyor; miktarı kontrol edin."
            )
    if qty is None:
        warnings.append("Miktar bulunamadı.")

    amount = parse_number(m.group(1)) if (m := _AMOUNT.search(without_dates)) else None
    price = None
    if found := _PRICE.search(without_dates):
        price = parse_number(found.group(1) or found.group(2))
    if price is None:
        euros = [parse_number(m.group(1)) for m in _PLAIN_EURO.finditer(without_dates)]
        euros = [e for e in euros if e is not None and e != amount]
        if euros:
            price = euros[0]
    if price is None and amount is not None and qty:
        price = (amount / qty).quantize(Decimal("0.0001"))
        warnings.append("Birim fiyat tutardan hesaplandı (tutar ÷ miktar).")
    if price is None:
        warnings.append("Birim fiyat bulunamadı.")
    if price is not None and amount is not None and qty is not None:
        computed = (qty * price).quantize(Decimal("0.01"))
        if abs(computed - amount) > Decimal("0.01"):
            warnings.append(
                f"Belgedeki tutar ({amount}) miktar × fiyattan ({computed}) farklı; kabulde açıklama gerekir."
            )
    if how == "benzer":
        warnings.append(f"Ürün adı tam eşleşmedi; '{product.name}' önerildi, kontrol edin.")
    return LineSuggestion(
        source=line[:300],
        product_id=product.id,
        product_code=product.code,
        product_name=product.name,
        match=how,
        qty=qty,
        unit=unit or expected_unit,
        unit_price=price,
        invoice_amount=amount,
        lot_no=lot_no,
        expiry_date=expiry,
        warnings=warnings,
    )
