"""JSON 存档 / 读档：多存档、命名、迁移。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

from .models import Character, Dynasty
from .time import Date
from .world import World

SAVE_VERSION = 2
SAVE_DIR = Path("saves")

# 旧档 log 的 emoji 前缀 -> 事件类型
_LEGACY_EMOJI = {
    "♡": "pregnancy",
    "👶": "birth",
    "⚭": "marriage",
    "⚰": "death",
    "👑": "succession",
    "☠": "extinction",
}


def _events_from_log(log: list[str]) -> list[dict]:
    """v1 存档无结构化事件，从字符串日志的 emoji 前缀合成（无日期）。"""
    events: list[dict] = []
    for msg in log:
        etype = "chronicle"
        text = msg
        for emoji, t in _LEGACY_EMOJI.items():
            if msg.startswith(emoji):
                etype = t
                text = msg[len(emoji):].strip()
                break
        else:
            if "成年了（" in msg:
                etype = "adulthood"
            elif "成为" in msg and "家主" in msg:
                etype = "succession"
        events.append(
            {"year": None, "month": None, "xun": None, "type": etype, "text": text, "actors": []}
        )
    return events


def _rng_state_to_json(state) -> list:
    version, internal, gauss_next = state
    return [version, list(internal), gauss_next]


def _rng_state_from_json(data) -> tuple:
    version, internal, gauss_next = data
    return (version, tuple(internal), gauss_next)


def world_to_dict(world: World) -> dict:
    return {
        "version": SAVE_VERSION,
        "date": world.date.to_dict(),
        "player_id": world.player_id,
        "next_char_id": world.next_char_id,
        "next_dynasty_id": world.next_dynasty_id,
        "gender_law": world.gender_law,
        "over": world.over,
        "over_reason": world.over_reason,
        "rng_state": _rng_state_to_json(world.rng.getstate()),
        "characters": [c.to_dict() for c in world.characters.values()],
        "dynasties": [d.to_dict() for d in world.dynasties.values()],
        "log": list(world.log),
        "events": [dict(e) for e in world.events],
        "naming_queue": [dict(e) for e in world.naming_queue],
        "tutoring_queue": [dict(e) for e in world.tutoring_queue],
        "betrothals": [dict(e) for e in world.betrothals],
    }


def world_from_dict(data: dict) -> World:
    world = World(date=Date.from_dict(data["date"]))
    world.player_id = data.get("player_id")
    world.next_char_id = data.get("next_char_id", 1)
    world.next_dynasty_id = data.get("next_dynasty_id", 1)
    world.gender_law = data.get("gender_law", "male_preference")
    world.over = data.get("over", False)
    world.over_reason = data.get("over_reason", "")
    if "rng_state" in data:
        world.rng.setstate(_rng_state_from_json(data["rng_state"]))
    for cdata in data.get("characters", []):
        char = Character.from_dict(cdata)
        world.characters[char.id] = char
    for ddata in data.get("dynasties", []):
        dyn = Dynasty.from_dict(ddata)
        world.dynasties[dyn.id] = dyn
    world.log = list(data.get("log", []))
    legacy_events = data.get("events")
    world.events = (
        [dict(e) for e in legacy_events] if legacy_events is not None else _events_from_log(world.log)
    )
    world.naming_queue = [dict(e) for e in data.get("naming_queue", [])]
    world.tutoring_queue = [dict(e) for e in data.get("tutoring_queue", [])]
    world.betrothals = [dict(e) for e in data.get("betrothals", [])]
    world.refresh_ages()
    return world


def save_world(world: World, path: str | Path, save_name: Optional[str] = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = world_to_dict(world)
    if save_name is not None:
        data["save_name"] = save_name
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return path


def load_world(path: str | Path) -> World:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return world_from_dict(data)


def safe_filename(name: str) -> str:
    bad = '<>:"/\\|?*'
    cleaned = "".join("_" if ch in bad else ch for ch in name).strip().strip(".")
    return cleaned or "未命名"


def default_name(world: World) -> str:
    player = world.player
    dyn = world.dynasty_name_of(player.id) if player else ""
    return f"{dyn}{world.date.year}年" if dyn else f"{world.date.year}年"


def save_path_for(name: str, save_dir: str | Path = SAVE_DIR) -> Path:
    return Path(save_dir) / f"{safe_filename(name)}.json"


def save_exists(name: str, save_dir: str | Path = SAVE_DIR) -> bool:
    return save_path_for(name, save_dir).exists()


def save_named(world: World, name: str, save_dir: str | Path = SAVE_DIR) -> Path:
    return save_world(world, save_path_for(name, save_dir), save_name=name)


def list_saves(save_dir: str | Path = SAVE_DIR) -> list[dict]:
    d = Path(save_dir)
    if not d.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(d.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        date = data.get("date", {})
        out.append(
            {
                "path": f,
                "name": data.get("save_name") or f.stem,
                "year": date.get("year", "?"),
                "month": date.get("month", "?"),
                "mtime": f.stat().st_mtime,
            }
        )
    out.sort(key=lambda s: s["mtime"], reverse=True)
    return out


def migrate_legacy(old_path: str | Path = "save.json", save_dir: str | Path = SAVE_DIR) -> Optional[Path]:
    old = Path(old_path)
    if not old.exists():
        return None
    try:
        world = load_world(old)
    except (OSError, ValueError, KeyError):
        return None
    target = save_path_for(default_name(world), save_dir)
    if target.exists():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(old), str(target))
    return target
