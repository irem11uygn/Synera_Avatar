"""Belge numaraları: <önek>-<yıl>-<sıra> (architecture.md §15). Satır kilidiyle artırılır."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NumberSequence

# Şartnamedeki biçimler: URT-2026-045 (3 hane); satış belgeleri 4 hane (SAT-2026-0101).
_WIDTH = {"URT": 3, "PRC": 3, "GC": 3}
_DEFAULT_WIDTH = 4


def next_document_no(session: Session, prefix: str, year: int) -> str:
    sequence = session.execute(
        select(NumberSequence)
        .where(NumberSequence.prefix == prefix, NumberSequence.year == year)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if sequence is None:
        sequence = NumberSequence(prefix=prefix, year=year, last_no=0)
        session.add(sequence)
    sequence.last_no += 1
    session.flush()
    return f"{prefix}-{year}-{sequence.last_no:0{_WIDTH.get(prefix, _DEFAULT_WIDTH)}d}"
