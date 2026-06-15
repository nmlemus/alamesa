"""Validate nginx cache-header rules in nginx/default.conf."""

import re
from pathlib import Path

CONF_PATH = Path(__file__).parent.parent / "nginx" / "default.conf"


def _block(conf: str, location_line_pattern: str) -> str:
    """Return the body of the first location block whose declaration matches *location_line_pattern*."""
    m = re.search(location_line_pattern, conf)
    assert m, f"No location matching {location_line_pattern!r} found in nginx config"
    start = conf.index("{", m.start())
    depth = 0
    for i, ch in enumerate(conf[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return conf[start : i + 1]
    raise AssertionError(f"Unclosed block for {location_line_pattern!r}")


def test_menu_endpoint_has_short_public_cache() -> None:
    conf = CONF_PATH.read_text()
    # Match the location line that ends with /menu (not /diners/register etc.)
    block = _block(conf, r"location\s*~\s*\^/api/public/[^{]*/menu")
    assert 'Cache-Control "public, max-age=30"' in block


def test_general_api_has_no_store() -> None:
    conf = CONF_PATH.read_text()
    block = _block(conf, r"location\s+/api/\s*\{")
    assert "Cache-Control no-store" in block


def test_assets_have_long_lived_immutable_cache() -> None:
    conf = CONF_PATH.read_text()
    block = _block(conf, r"location\s+/assets/\s*\{")
    assert "max-age=31536000" in block
    assert "immutable" in block


def test_menu_block_appears_before_general_api_block() -> None:
    conf = CONF_PATH.read_text()
    menu_m = re.search(r"location\s*~\s*\^/api/public/[^{]*/menu", conf)
    api_m = re.search(r"location\s+/api/\s*\{", conf)
    assert menu_m, "Menu cache location block not found"
    assert api_m, "General /api/ location block not found"
    assert menu_m.start() < api_m.start(), (
        "Menu cache location must appear before the general /api/ block "
        "so nginx regex matching picks it up first"
    )
