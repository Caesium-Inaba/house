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
_current_lang = "zh"


def set_language(lang: str) -> None:
    """设置全局展示语言（单机服务器单会话，快照渲染前统一设置）。"""
    global _current_lang
    _current_lang = lang if lang in ("zh", "en") else "zh"


def current_language() -> str:
    return _current_lang


def _locale(lang: str) -> dict[str, Any]:
    if lang not in _cache:
        path = _LOCALES_DIR / f"{lang}.json"
        base: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        # 模组语言包按键覆盖（启用顺序，越靠后越优先）
        from .core import mods

        for overlay in mods.locale_overlays(lang):
            for k, v in overlay.items():
                base[k] = v
        _cache[lang] = base
    return _cache[lang]


def reload_data() -> None:
    """重读全部语言包（模组激活/关闭后由 traits.reload_data 一并触发）。"""
    _cache.clear()


def t(key: str, /, lang: str | None = None, **params) -> str:
    """翻译键 —— 模板用 {name} 之类的占位符；语言缺省用全局设置。"""
    table = _locale(lang or _current_lang)
    template = table.get(key)
    if template is None:
        return key
    try:
        return template.format(**params)
    except (KeyError, IndexError):
        return template


def has_key(key: str, lang: str = "zh") -> bool:
    return key in _locale(lang)
