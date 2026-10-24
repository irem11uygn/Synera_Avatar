"""Ağırlık dengesi (AT-04) ve lot ağında gezinme (saf fonksiyonlar)."""

from decimal import Decimal as D

from app.domain.balance import weight_balance
from app.domain.graph import traverse

PARTS_KG = [D("7"), D("4"), D("5"), D("3"), D("3")]  # 22 kg


def test_at04_unexplained_3_kg_breaks_the_balance():
    balance = weight_balance(D("25"), PARTS_KG, tolerance_kg=D("0.200"))
    assert balance.outputs_kg == D("22")
    assert balance.difference_kg == D("3")
    assert not balance.ok


def test_at04_balance_holds_once_fire_is_recorded():
    assert weight_balance(D("25"), [*PARTS_KG, D("3")], tolerance_kg=D("0.200")).ok


def test_small_weighing_difference_within_tolerance():
    assert weight_balance(D("25"), [*PARTS_KG, D("2.850")], tolerance_kg=D("0.200")).ok
    assert not weight_balance(D("25"), [*PARTS_KG, D("2.750")], tolerance_kg=D("0.200")).ok


def _graph(edges: dict[int, list[int]]):
    return lambda frontier: [child for node in frontier for child in edges.get(node, [])]


def test_traverse_follows_many_to_many_links_with_depth():
    # 1 (et) ve 2 (baharat) → 3 (sucuk); 3 → 4 (yeniden işlenmiş); 1 → 5 (başka emir)
    edges = {1: [3, 5], 2: [3], 3: [4]}
    assert traverse(1, _graph(edges)) == {1: 0, 3: 1, 5: 1, 4: 2}
    assert traverse(2, _graph(edges)) == {2: 0, 3: 1, 4: 2}


def test_traverse_terminates_on_cycles():
    assert traverse(1, _graph({1: [2], 2: [3], 3: [1]})) == {1: 0, 2: 1, 3: 2}


def test_traverse_single_node():
    assert traverse(7, _graph({})) == {7: 0}
