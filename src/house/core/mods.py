"""模组系统（CK3 原版精神）：mods/ 目录树 + launcher.json 启用清单 + 数据覆盖层。

结构对齐 CK3/Jomini 的惯例：

- 每个 mod 一个文件夹：``mods/<文件夹>/mod.json`` 描述符
  （{"name", "version", "supported_version", "tags":[...]}），内容可选：
  - ``data/<file>.json``        按键深合并进同名原版数据（数组/标量整值覆盖）
  - ``localization/<lang>.json`` 按键覆盖原版语言包
- 启用清单存 ``launcher.json``（等价 CK3 的 dlc_load.json / 默认 playset）：
  {"enabled": ["文件夹A", "文件夹B"]}
- 载入顺序＝列表顺序：从上往下加载，**越靠下越优先**（对齐 CK3 启动器语义，
  Paradox 官方论坛：「Whatever is at top is loaded first …」）。
- 目录跟随进程工作目录（exe 双击 = exe 目录），与 saves/ 同惯例。
- 本模块只做扫描与覆盖层，不 import traits/i18n（防循环）；数据重载入口在
  traits.reload_data()。
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

MODS_DIR_NAME = "mods"
CONFIG_NAME = "launcher.json"


@dataclass
class ModInfo:
    folder: str
    name: str = ""
    version: str = ""
    supported_version: str = ""
    tags: list[str] = field(default_factory=list)
    valid: bool = False
    error: str = ""


def mods_root(base: pathlib.Path | None = None) -> pathlib.Path:
    if base is not None:
        return base / MODS_DIR_NAME
    return pathlib.Path.cwd() / MODS_DIR_NAME


def config_path(base: pathlib.Path | None = None) -> pathlib.Path:
    if base is not None:
        return base / CONFIG_NAME
    return pathlib.Path.cwd() / CONFIG_NAME


def load_config(base: pathlib.Path | None = None) -> dict[str, list[str]]:
    """读取 launcher.json；缺失/坏档按空清单处理。"""
    path = config_path(base)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("enabled"), list):
            return {"enabled": [str(x) for x in data["enabled"]]}
    except (OSError, ValueError):
        pass
    return {"enabled": []}


def save_config(enabled: list[str], base: pathlib.Path | None = None) -> None:
    path = config_path(base)
    path.write_text(
        json.dumps({"enabled": [str(x) for x in enabled]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def scan(base: pathlib.Path | None = None) -> list[ModInfo]:
    """扫描 mods/ 下的全部模组（坏档标记 invalid，不崩溃）。"""
    root = mods_root(base)
    infos: list[ModInfo] = []
    if not root.is_dir():
        return infos
    for folder in sorted(p.name for p in root.iterdir() if p.is_dir()):
        info = ModInfo(folder=folder)
        try:
            desc = json.loads((root / folder / "mod.json").read_text(encoding="utf-8"))
            info.name = str(desc.get("name") or folder)
            info.version = str(desc.get("version") or "")
            info.supported_version = str(desc.get("supported_version") or "")
            tags = desc.get("tags")
            info.tags = [str(t) for t in tags] if isinstance(tags, list) else []
            info.valid = True
        except (OSError, ValueError):
            info.error = "无法读取 mod.json"
        infos.append(info)
    return infos


def enabled_folders(base: pathlib.Path | None = None) -> list[str]:
    return load_config(base)["enabled"]


def _enabled_mods(base: pathlib.Path | None = None) -> list[str]:
    """按序返回有效 mod 文件夹；清单里不存在的文件夹跳过。"""
    root = mods_root(base)
    out: list[str] = []
    for folder in load_config(base)["enabled"]:
        if (root / folder).is_dir():
            out.append(folder)
    return out


def data_overlays(relpath: str, base: pathlib.Path | None = None) -> list[dict[str, Any]]:
    """某数据文件的全部模组覆盖，按启用顺序排列（后者优先）。"""
    root = mods_root(base)
    out: list[dict[str, Any]] = []
    for folder in _enabled_mods(base):
        p = root / folder / "data" / relpath
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            out.append(data)
    return out


def locale_overlays(lang: str, base: pathlib.Path | None = None) -> list[dict[str, Any]]:
    """某语言包的全部模组覆盖（扁平键，后者优先）。"""
    root = mods_root(base)
    out: list[dict[str, Any]] = []
    for folder in _enabled_mods(base):
        p = root / folder / "localization" / f"{lang}.json"
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            out.append(data)
    return out


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """按键深合并（CK3 registry 语义）：dict 递归，数组/标量/null 整值覆盖。原地改 base。"""
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base
