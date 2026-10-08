"""婚姻（M2 最简版）：安排婚配、候选筛选、好感初始化。"""

from __future__ import annotations

from typing import Optional

from .. import balance as B
from . import opinion
from .models import Character
from .world import World

MARRIAGE_MAX_AGE = 55


def can_marry(world: World, char: Character, other: Character) -> bool:
    if char.id == other.id:
        return False
    if not char.is_alive or not other.is_alive:
        return False
    if char.spouse is not None or other.spouse is not None:
        return False
    if char.gender == other.gender:
        return False
    if not char.is_adult or not other.is_adult:
        return False
    if char.age > MARRIAGE_MAX_AGE or other.age > MARRIAGE_MAX_AGE:
        return False
    return True


def candidates(world: World, char_id: int) -> list[Character]:
    char = world.get(char_id)
    if char is None:
        return []
    out = [c for c in world.alive() if can_marry(world, char, c)]
    out.sort(key=lambda c: (c.gender, c.age))
    return out


def arrange_marriage(
    world: World, a_id: int, b_id: int, patrilineal: Optional[bool] = None
) -> bool:
    a, b = world.get(a_id), world.get(b_id)
    if a is None or b is None or not can_marry(world, a, b):
        return False
    if patrilineal is None:
        patrilineal = a.gender == "male"
    a.spouse, b.spouse = b.id, a.id
    a.patrilineal = b.patrilineal = patrilineal
    opinion.add_opinion(a, b.id, 30)
    opinion.add_opinion(b, a.id, 30)
    world.add_log(f"⚭ {a.name} 与 {b.name} 缔结姻缘。")
    world.add_event("marriage", f"{a.name} 与 {b.name} 缔结姻缘。", [a.id, b.id])
    return True


def ai_marriages(world: World, chance: float = 0.03) -> None:
    """NPC 自动婚配（M2 占位），保证家族血脉延续，避免人口雪崩。

    用世界规模软上限节流：接近上限时婚配概率线性下降，达硬上限则停止。
    """
    alive = len(world.alive())
    if alive >= B.WORLD_HARD_CAP:
        return
    if alive > B.WORLD_SOFT_CAP:
        span = B.WORLD_HARD_CAP - B.WORLD_SOFT_CAP
        chance *= max(0.0, 1.0 - (alive - B.WORLD_SOFT_CAP) / span)
    singles = [
        c
        for c in world.alive()
        if c.spouse is None and c.is_adult and c.age <= MARRIAGE_MAX_AGE and c.id != world.player_id
    ]
    world.rng.shuffle(singles)
    for c in singles:
        if c.spouse is not None or world.rng.random() > chance:
            continue
        options = [
            o
            for o in singles
            if o.spouse is None and o.id != c.id and o.gender != c.gender and o.id != world.player_id
        ]
        if not options:
            continue
        arrange_marriage(world, c.id, world.rng.choice(options).id)
