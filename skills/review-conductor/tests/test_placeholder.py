"""Shared placeholder detection has a single source of truth used by both
aggregate_panel and outcomes_loader (no duplicated drift-prone copies)."""


def test_is_placeholder_recognizes_variants():
    from scripts.placeholder import is_placeholder
    for text in ["_(none)_", "(none)", "_none_", "none", "  NONE  ", "*-none-*"]:
        assert is_placeholder(text), text


def test_is_placeholder_rejects_real_findings():
    from scripts.placeholder import is_placeholder
    assert not is_placeholder("a real critical finding")
    assert not is_placeholder("none of the citations resolve")


def test_aggregate_and_outcomes_share_one_implementation():
    from scripts import placeholder, aggregate_panel, outcomes_loader
    # Both modules must reference the shared implementation, not private copies.
    assert aggregate_panel._is_placeholder is placeholder.is_placeholder
    assert outcomes_loader._is_placeholder is placeholder.is_placeholder
