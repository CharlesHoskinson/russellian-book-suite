import os
import pytest


def test_live_llm_imports_without_key():
    """Importing live_llm must not require ANTHROPIC_API_KEY to be set."""
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        from scripts import live_llm  # noqa: F401
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def test_extract_llm_raises_clear_runtime_error_without_key():
    """Calling extract_llm without ANTHROPIC_API_KEY raises a clear RuntimeError, not a network error."""
    from scripts.live_llm import extract_llm
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            extract_llm("hello")
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def test_cross_check_llm_raises_clear_runtime_error_without_key():
    from scripts.live_llm import cross_check_llm
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            cross_check_llm("hello")
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def test_generate_raises_clear_runtime_error_without_key():
    from scripts.live_llm import generate
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            generate("hello", model="claude-opus-4-7", max_tokens=100)
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved
