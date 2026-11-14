from core.offline_anchor import MonotonicAnchor


def test_anchor_survives_restart_and_rejects_rollback(tmp_path):
    path = str(tmp_path / "anchor.db")
    anchor = MonotonicAnchor(path)
    assert anchor.accept(10, "snap-10") is True
    anchor.close()

    reopened = MonotonicAnchor(path)
    assert reopened.current() == (10, "snap-10")
    assert reopened.accept(9, "snap-9") is False
    assert reopened.accept(10, "other") is False
    assert reopened.accept(11, "snap-11") is True
    reopened.close()
