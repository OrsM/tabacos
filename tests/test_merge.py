from tabacos.merge import merge_latest


def test_newer_report_wins_and_each_change_is_reported():
    old = ("jan.pdf", [("A", 1, 10), ("B", 1, 20)])
    new = ("feb.pdf", [("A", 1, 11), ("C", 2, 30)])
    winners, revisions = merge_latest([old, new], key=lambda f: (f[0], f[1]), value=lambda f: f[2])
    assert {f: s for f, s in winners} == {("A", 1, 11): "feb.pdf", ("B", 1, 20): "jan.pdf", ("C", 2, 30): "feb.pdf"}
    assert revisions == [{"key": ("A", 1), "old": 10, "new": 11, "old_source": "jan.pdf", "new_source": "feb.pdf"}]


def test_same_value_in_two_reports_is_not_a_revision():
    r = [("a.pdf", [("A", 1, 5)]), ("b.pdf", [("A", 1, 5)])]
    winners, revisions = merge_latest(r, key=lambda f: (f[0], f[1]), value=lambda f: f[2])
    assert revisions == [] and len(winners) == 1
