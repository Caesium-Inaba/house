"""JSON 存档 / 读档。"""

from __future__ import annotations

import json
from pathlib import Path

from .models import Character, Dynasty
from .time import Date
from .world import World

SAVE_VERSION = 1


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
    world.refresh_ages()
    return world


def save_world(world: World, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(
        json.dumps(world_to_dict(world), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return path


def load_world(path: str | Path) -> World:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return world_from_dict(data)
