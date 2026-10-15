"""Optional browser components. SDK imports and binary installation happen on first use."""

from shadow_hdk.adapters.browser.components import BrowserComponents, BrowserEngine
from shadow_hdk.adapters.browser.engine import PlaywrightEngine
from shadow_hdk.adapters.browser.policy import OriginPolicy

__all__ = [
    "BrowserComponents",
    "BrowserEngine",
    "OriginPolicy",
    "PlaywrightEngine",
]
