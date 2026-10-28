"""Geri çağırma ve uyarılar (FR-306, FR-307, FR-310)."""

from decimal import Decimal

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.csv_export import csv_response
from app.api.deps import Db, QualityUser, WebUser
from app.api.fields import UtcDateTime
from app.api.trace import RecipientOut, StockItemOut, TracedLotOut
from app.models import Recall
from app.models.enums import RecallResolution, RecallStatus, Severity
from app.services import alarms, audit
from app.services.lookups import get_or_404
from app.services.recall import (
    RecallView,
    close_recall,
    held_by_customers,
    recall_view,
    start_recall,
)
from app.services.trace import OnwardStatus

router = APIRouter(prefix="/recalls", tags=["geri çağırma"])

ONWARD_TEXT = {
    OnwardStatus.KAYITLI: "Kesin (kayıtlı)",
    OnwardStatus.KISMEN: "Kısmen kayıtlı; kalanı bilinmiyor",
    OnwardStatus.BILINMIYOR: "Bilinen son alıcı; sonrası bilinmiyor",
}


class RecallIn(BaseModel):
    lot_no: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=1, max_length=500)


class RecallCloseIn(BaseModel):
    resolution: RecallResolution
    note: str | None = Field(default=None, max_length=500)


class RecallSummaryOut(BaseModel):
    id: int
    recall_no: str
    source_lot_no: str
    reason: str
    status: RecallStatus
    resolution: RecallResolution | None
    started_at: UtcDateTime
    started_by_name: str | None
    closed_at: UtcDateTime | None
    close_note: str | None
    lot_count: int
    customer_count: int
    violation_count: int
    held_by_customers: dict[str, Decimal]


class RecallOut(RecallSummaryOut):
    lots: list[TracedLotOut]
    stock: list[StockItemOut]
    recipients: list[RecipientOut]


def _summary(view: RecallView) -> dict:
    recall = view.recall
    return {
        "id": recall.id,
        "recall_no": recall.recall_no,
        "source_lot_no": view.source_lot_no,
        "reason": recall.reason,
        "status": recall.status,
        "resolution": recall.resolution,
        "started_at": recall.started_at,
        "started_by_name": view.started_by_name,
        "closed_at": recall.closed_at,
        "close_note": recall.close_note,
        "lot_count": len(view.lots),
        "customer_count": view.customer_count,
        "violation_count": view.violation_count,
        "held_by_customers": held_by_customers(view),
    }


def _recall_out(view: RecallView) -> RecallOut:
    return RecallOut.model_validate(
        {
            **_summary(view),
            "lots": [TracedLotOut.model_validate(lot) for lot in view.lots],
            "stock": [StockItemOut.model_validate(item) for item in view.stock],
            "recipients": [RecipientOut.model_validate(r) for r in view.recipients],
        }
    )


@router.post("", response_model=RecallOut, status_code=201)
def create(body: RecallIn, db: Db, user: QualityUser) -> RecallOut:
    """Kaynak lot ve bütün türevleri tek işlemde bloke edilir; liste hemen döner."""
    recall = start_recall(db, lot_no=body.lot_no.strip(), reason=body.reason, user_id=user.id)
    view = recall_view(db, recall)
    audit.log(
        db,
        "GERI_CAGIRMA",
        f"{recall.recall_no} başlatıldı: kaynak {view.source_lot_no}, {len(view.lots)} lot bloke, "
        f"{view.customer_count} müşteri. Neden: {recall.reason}",
        user=user,
        severity=Severity.KRITIK,
        ref_type="RECALL",
        ref_id=recall.id,
    )
    alarms.recall_started(db, recall, user, view.source_lot_no, max(len(view.lots) - 1, 0))
    alarms.run_rules(db, user)  # bloke lotta stok kalmışsa hemen görünsün
    return _recall_out(view)


@router.get("", response_model=list[RecallSummaryOut])
def list_recalls(db: Db, _: WebUser) -> list[RecallSummaryOut]:
    recalls = db.scalars(select(Recall).order_by(Recall.id.desc())).all()
    return [RecallSummaryOut.model_validate(_summary(recall_view(db, r))) for r in recalls]


@router.get("/{recall_id}", response_model=RecallOut)
def get_recall(recall_id: int, db: Db, _: WebUser) -> RecallOut:
    return _recall_out(recall_view(db, get_or_404(db, Recall, recall_id, "Geri çağırma")))


@router.get("/{recall_id}/export.csv", response_class=Response)
def export_csv(recall_id: int, db: Db, _: WebUser) -> Response:
    """İletişim listesi: müşteri × lot başına bir satır, ikinci kademe alıcılar ayrı satırlarda."""
    view = recall_view(db, get_or_404(db, Recall, recall_id, "Geri çağırma"))
    header = [
        "Geri çağırma",
        "Kademe",
        "Alıcı",
        "Yetkili",
        "Telefon",
        "E-posta",
        "Adres",
        "Lot",
        "Ürün",
        "Miktar",
        "Birim",
        "Satış belgeleri",
        "Sonrası",
        "Çevrimdışı ihlal",
    ]
    rows: list[list[object]] = []
    for r in view.recipients:
        unit = "kg" if r.base_unit == "KG" else "adet"
        documents = ", ".join(s.sale_no for s in r.sales)
        rows.append(
            [
                view.recall.recall_no,
                "1 (müşteri)",
                r.customer,
                r.contact.person,
                r.contact.phone,
                r.contact.email,
                r.contact.address,
                r.lot_no,
                r.product_name,
                r.qty,
                unit,
                documents,
                ONWARD_TEXT[r.onward_status],
                r.recall_violation,
            ]
        )
        for item in r.onward_items:
            rows.append(
                [
                    view.recall.recall_no,
                    f"2 ({r.customer} alıcısı)",
                    item.recipient,
                    item.contact.person,
                    item.contact.phone,
                    item.contact.email,
                    item.contact.address,
                    r.lot_no,
                    r.product_name,
                    item.qty,
                    unit,
                    documents,
                    "Kesin (müşterinin bildirimi)",
                    False,
                ]
            )
    return csv_response(f"{view.recall.recall_no}_iletisim_listesi.csv", header, rows)


@router.post("/{recall_id}/close", response_model=RecallOut)
def close(recall_id: int, body: RecallCloseIn, db: Db, user: QualityUser) -> RecallOut:
    recall = close_recall(db, recall_id, resolution=body.resolution, note=body.note, user_id=user.id)
    audit.log(
        db,
        "GERI_CAGIRMA_KAPANDI",
        f"{recall.recall_no} kapatıldı: "
        + ("imha" if body.resolution == RecallResolution.IMHA else "serbest bırakıldı")
        + (f" — {body.note}" if body.note else ""),
        user=user,
        severity=Severity.UYARI,
        ref_type="RECALL",
        ref_id=recall.id,
    )
    return _recall_out(recall_view(db, recall))
