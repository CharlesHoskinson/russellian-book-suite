"""Detect whether Playwright + Chromium are installed.

Used by tests and build_book to skip / degrade rather than crash when the
optional Chromium component has not been installed.
"""
from __future__ import annotations


class PlaywrightUnavailable(Exception):
    """Raised when Playwright import fails or Chromium is not installed."""


def is_playwright_ready() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    try:
        with sync_playwright() as p:
            browsers_path = p.chromium.executable_path
            from pathlib import Path
            return Path(browsers_path).exists()
    except Exception:
        return False
