"""好感度（Opinion）：-100..100。

CK3 无全局月度衰减；好感是持久的 modifier，由事件与关系产生。
"""

from __future__ import annotations

from .models import Character
from .world import World

MONTHLY_DECAY_STEP = 0.0  # CK3 无衰减；保留开关便于试玩调校


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
