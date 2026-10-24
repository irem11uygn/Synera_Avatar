"""Defter ve özetlerin tutarlılık denetimi: değişmezler I-1…I-8 (data_model.md §5, FR-607, AT-10)."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import Row, text
from sqlalchemy.orm import Session

DESCRIPTIONS = {
    "I-1": "Lotun kalan miktarı, hareketlerinin miktar toplamına eşit",
    "I-2": "Lotun kalan değeri, hareketlerinin değer toplamına eşit",
    "I-3": "Depo bakiyesi, o depodaki hareketlerin miktar toplamına eşit",
    "I-4": "Miktarı sıfır olan lotun değeri de sıfır",
    "I-5": "Onaylı parçalamada dağıtılan maliyet = toplam maliyet ve ağırlık dengesi tolerans içinde",
    "I-6": "Tamamlanan üretimde mamul lot değeri = tüketim değeri + hizmet tutarı",
    "I-7": "Her satış satırının hareketi aynı lot ve miktarda",
    "I-8": "Alış dışında oluşan her lotun en az bir kaynak lotu var",
}


@dataclass(frozen=True)
class InvariantResult:
    code: str
    description: str
    violations: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


def check_invariants(session: Session) -> list[InvariantResult]:
    lot_rows = session.execute(
        text(
            """
            SELECT l.lot_no, l.remaining_qty, l.remaining_value,
                   COALESCE(SUM(m.qty), 0) AS moved_qty, COALESCE(SUM(m.value), 0) AS moved_value
            FROM lots l LEFT JOIN stock_movements m ON m.lot_id = l.id
            GROUP BY l.id, l.lot_no, l.remaining_qty, l.remaining_value
            """
        )
    ).all()
    violations = {
        "I-1": _lot_qty_violations(lot_rows),
        "I-2": _lot_value_violations(lot_rows),
        "I-3": _balance_violations(session),
        "I-4": _empty_lot_value_violations(lot_rows),
        "I-5": _cutting_violations(session),
        "I-6": _production_violations(session),
        "I-7": _sale_line_violations(session),
        "I-8": _orphan_lot_violations(session),
    }
    return [InvariantResult(code, DESCRIPTIONS[code], found) for code, found in violations.items()]


def _lot_qty_violations(rows: Sequence[Row]) -> list[str]:
    return [f"{r.lot_no}: özet {r.remaining_qty}, hareketler {r.moved_qty}" for r in rows
            if r.remaining_qty != r.moved_qty]  # fmt: skip


def _lot_value_violations(rows: Sequence[Row]) -> list[str]:
    return [f"{r.lot_no}: özet {r.remaining_value}, hareketler {r.moved_value}" for r in rows
            if r.remaining_value != r.moved_value]  # fmt: skip


def _empty_lot_value_violations(rows: Sequence[Row]) -> list[str]:
    return [f"{r.lot_no}: kalan değer {r.remaining_value}" for r in rows
            if r.remaining_qty == 0 and r.remaining_value != 0]  # fmt: skip


def _balance_violations(session: Session) -> list[str]:
    rows = session.execute(
        text(
            """
            SELECT l.lot_no, w.code AS warehouse, COALESCE(b.qty, 0) AS balance, SUM(m.qty) AS moved
            FROM stock_movements m
            JOIN lots l ON l.id = m.lot_id
            JOIN warehouses w ON w.id = m.warehouse_id
            LEFT JOIN stock_balances b ON b.lot_id = m.lot_id AND b.warehouse_id = m.warehouse_id
            GROUP BY l.lot_no, w.code, b.qty
            HAVING COALESCE(b.qty, 0) <> SUM(m.qty)
            """
        )
    ).all()
    return [f"{r.lot_no} @ {r.warehouse}: bakiye {r.balance}, hareketler {r.moved}" for r in rows]


def _cutting_violations(session: Session) -> list[str]:
    rows = session.execute(
        text(
            """
            SELECT c.cutting_no, c.total_cost, c.input_qty, r.tolerance_kg,
                   COALESCE(SUM(o.allocated_cost), 0) AS allocated, COALESCE(SUM(o.actual_qty), 0) AS outputs
            FROM cuttings c
            JOIN cutting_recipes r ON r.id = c.recipe_id
            LEFT JOIN cutting_outputs o ON o.cutting_id = c.id
            WHERE c.status = 'ONAYLANDI'
            GROUP BY c.id, c.cutting_no, c.total_cost, c.input_qty, r.tolerance_kg
            """
        )
    ).all()
    found = []
    for r in rows:
        if r.allocated != r.total_cost:
            found.append(f"{r.cutting_no}: dağıtılan {r.allocated} ≠ toplam {r.total_cost}")
        if abs(r.input_qty - r.outputs) > r.tolerance_kg:
            found.append(f"{r.cutting_no}: giriş {r.input_qty} kg, çıkışlar {r.outputs} kg")
    return found


def _production_violations(session: Session) -> list[str]:
    rows = session.execute(
        text(
            """
            SELECT po.order_no, l.initial_value, COALESCE(po.service_amount, 0) AS service,
                   (SELECT COALESCE(-SUM(m.value), 0) FROM stock_movements m
                    WHERE m.doc_type = 'URETIM' AND m.doc_id = po.id
                      AND m.type = 'URETIM_TUKETIM') AS consumed
            FROM production_orders po JOIN lots l ON l.id = po.output_lot_id
            WHERE po.status = 'TAMAMLANDI'
            """
        )
    ).all()
    return [
        f"{r.order_no}: mamul değeri {r.initial_value} ≠ tüketim {r.consumed} + hizmet {r.service}"
        for r in rows
        if r.initial_value != r.consumed + r.service
    ]


def _sale_line_violations(session: Session) -> list[str]:
    rows = session.execute(
        text(
            """
            SELECT s.sale_no, sl.line_no FROM sale_lines sl
            JOIN sales s ON s.id = sl.sale_id
            JOIN stock_movements m ON m.id = sl.stock_movement_id
            WHERE m.lot_id <> sl.lot_id OR m.qty <> -sl.qty
            """
        )
    ).all()
    return [f"{r.sale_no} satır {r.line_no}" for r in rows]


def _orphan_lot_violations(session: Session) -> list[str]:
    rows = session.execute(
        text(
            """
            SELECT l.lot_no FROM lots l
            WHERE l.origin <> 'ALIS'
              AND NOT EXISTS (SELECT 1 FROM lot_links k WHERE k.child_lot_id = l.id)
            """
        )
    ).all()
    return [r.lot_no for r in rows]
