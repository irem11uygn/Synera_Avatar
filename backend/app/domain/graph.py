"""Lot ağında gezinme (FR-304, FR-305). Kesin kayıt ilişkilerine dayanır, tahmin içermez (CON-003)."""

from collections.abc import Callable, Collection, Iterable


def traverse(start: int, neighbours: Callable[[Collection[int]], Iterable[int]]) -> dict[int, int]:
    """start'tan erişilebilen düğümler ve derinlikleri (start = 0).

    Katman katman ilerler; her katmanın komşuları tek çağrıyla istenir (tek sorgu).
    Ziyaret edilen düğüm tekrar eklenmez, bu yüzden döngülü veride de sonlanır.
    """
    depth = {start: 0}
    frontier = [start]
    level = 0
    while frontier:
        level += 1
        next_frontier = []
        for node in neighbours(frontier):
            if node not in depth:
                depth[node] = level
                next_frontier.append(node)
        frontier = next_frontier
    return depth
