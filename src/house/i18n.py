"""轻量 i18n：t(key, **params) 从 data/locales/<lang>.json 取模板插值。

- 缺键回退原 key 显示（开发期可立即发现漏译）。
- 默认 zh；后续可在 server 层按请求切语言（快照工厂参数化）。
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

_LOCALES_DIR = pathlib.Path(__file__).resolve().parent / "data" / "locales"
_cache: dict[str, dict[str, Any]] = {}


def _locale(lang: str) -> dict[str, Any]:
    if lang not in _cache:
        path = _LOCALES_DIR / f"{lang}.json"
        _cache[lang] = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return _cache[lang]


def t(key: str, /, lang: str = "zh", **params) -> str:
    """翻译键 —— 模板用 {name} 之类的占位符。"""
    table = _locale(lang)
    template = table.get(key)
    if template is None:
        return key
    try:
        return template.format(**params)
    except (KeyError, IndexError):
        return template


def has_key(key: str, lang: str = "zh") -> bool:
    return key in _locale(lang)
