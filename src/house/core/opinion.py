"""好感度（Opinion）：-100..100，随时间向 0 衰减。"""

from __future__ import annotations

from .models import Character
from .world import World

MONTHLY_DECAY_STEP = 0.5


def set_opinion(char: Character, other_id: int, value: int) -> None:
    char.opinions[other_id] = max(-100, min(100, int(value)))


def add_opinion(char: Character, other_id: int, delta: int) -> None:
    set_opinion(char, other_id, char.opinions.get(other_id, 0) + delta)


def monthly_decay(world: World) -> None:
    for char in world.alive():
        for oid in list(char.opinions):
            v = char.opinions[oid]
            if v > 0:
                v = max(0, v - MONTHLY_DECAY_STEP)
            elif v < 0:
                v = min(0, v + MONTHLY_DECAY_STEP)
            char.opinions[oid] = int(v)
