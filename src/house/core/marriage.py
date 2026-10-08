"""婚姻与婚约：联姻、订婚（betrothal）、母系婚姻、近亲禁令（CK3 默认教义）。"""

from __future__ import annotations

from typing import Optional

from .. import balance as B
from . import opinion
from . import traits as T
from .models import Character
from .world import World

MARRIAGE_MAX_AGE = 55
BETROTHAL_MIN_AGE = 6  # 幼年即可订婚，但 16 岁前不圆婚


def _share_parent(a: Optional[Character], b: Optional[Character]) -> bool:
    return bool(
        a and b and a.id != b.id
        and ((a.father is not None and a.father == b.father) or (a.mother is not None and a.mother == b.mother))
    )


def kin_banned(world: World, a: Character, b: Character) -> bool:
    """CK3 默认「表亲可婚」教义：直系血亲、同胞/半血、叔伯姑姨甥禁止。"""
    if world.is_descendant(b.id, a.id) or world.is_descendant(a.id, b.id):
        return True  # 亲子 / 祖孙
    if _share_parent(a, b):
        return True  # 兄弟姐妹 / 半血
    for pa in (a.father, a.mother):
        if pa is not None and _share_parent(world.get(pa), b):
            return True  # b 是 a 的叔伯姑姨（反之同）
    for pb in (b.father, b.mother):
        if pb is not None and _share_parent(world.get(pb), a):
            return True
    return False


def can_marry(world: World, char: Character, other: Character) -> bool:
    if char.id == other.id:
        return False
    if not char.is_alive or not other.is_alive:
        return False
    if char.spouse is not None or other.spouse is not None:
        return False
    # 有婚约者只能与婚约对象成婚，不能再许第三者
    if char.betrothed is not None and char.betrothed != other.id:
        return False
    if other.betrothed is not None and other.betrothed != char.id:
        return False
    if char.gender == other.gender:
        return False
    if not char.is_adult or not other.is_adult:
        return False
    if char.age > MARRIAGE_MAX_AGE or other.age > MARRIAGE_MAX_AGE:
        return False
    if kin_banned(world, char, other):
        return False
    return True


def candidates(world: World, char_id: int) -> list[Character]:
    char = world.get(char_id)
    if char is None:
        return []
    out = [c for c in world.alive() if can_marry(world, char, c)]
    out.sort(key=lambda c: (c.gender, c.age))
    return out


def _apply_marriage_opinions(world: World, a: Character, b: Character) -> None:
    """CK3 婚姻好感：基础 +30，性格矩阵修饰。"""
    base = 30
    opinion.add_opinion(a, b.id, base + T.opinion_delta(a.traits, b.traits))
    opinion.add_opinion(b, a.id, base + T.opinion_delta(b.traits, a.traits))


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
    _apply_marriage_opinions(world, a, b)
    world.add_log(f"⚭ {a.name} 与 {b.name} 缔结姻缘。")
    world.add_event("marriage", f"{a.name} 与 {b.name} 缔结姻缘。", [a.id, b.id])
    return True


def can_betrothal(world: World, a: Character, b: Character) -> bool:
    if a.id == b.id:
        return False
    for c in (a, b):
        if not c.is_alive or c.is_adult or c.age < BETROTHAL_MIN_AGE:
            return False
        if c.spouse is not None or c.betrothed is not None:
            return False
    if a.gender == b.gender:
        return False
    if kin_banned(world, a, b):
        return False
    return True


def arrange_betrothal(
    world: World, a_id: int, b_id: int, patrilineal: Optional[bool] = None
) -> bool:
    """为一个或两个未成年的家族孩子订婚；16 岁后自动圆婚。"""
    a, b = world.get(a_id), world.get(b_id)
    if a is None or b is None or not can_betrothal(world, a, b):
        return False
    if patrilineal is None:
        patrilineal = a.gender == "male"  # 缺省从男性血脉
    world.betrothals.append({"a": a.id, "b": b.id, "patrilineal": patrilineal})
    a.betrothed, b.betrothed = b.id, a.id
    opinion.add_opinion(a, b.id, 10)
    opinion.add_opinion(b, a.id, 10)
    world.add_log(f"💍 {a.name} 与 {b.name} 缔结婚约（{'母系' if not patrilineal else '父系'}）。")
    world.add_event(
        "betrothal",
        f"{a.name} 与 {b.name} 缔结婚约（{'母系' if not patrilineal else '父系'}）。",
        [a.id, b.id],
    )
    return True


def fulfill_betrothals(world: World) -> None:
    """月度结算：双方满 16 岁且健在则自动圆婚；任一方先亡则婚约落空。"""
    for bd in list(world.betrothals):
        a, b = world.get(bd.get("a")), world.get(bd.get("b"))
        if a is None or b is None or not a.is_alive or not b.is_alive:
            world.betrothals.remove(bd)
            if a is not None:
                a.betrothed = None
            if b is not None:
                b.betrothed = None
            if a is not None and b is not None:
                world.add_log(f"💔 {a.name} 与 {b.name} 的婚约因变故落空。")
            continue
        if a.age >= B.CHILDHOOD_END and b.age >= B.CHILDHOOD_END:
            ok = arrange_marriage(world, a.id, b.id, patrilineal=bd.get("patrilineal"))
            world.betrothals.remove(bd)
            a.betrothed = None
            b.betrothed = None
            if not ok:
                world.add_log(f"💔 {a.name} 与 {b.name} 婚约期满却未能成婚。")


def betrothal_pools(world: World, player_id: int) -> tuple[list[Character], list[Character]]:
    """订婚候选池：自家孩子 / 他人家孩子（6-15 岁、未婚、没订婚）。"""
    own: list[Character] = []
    other: list[Character] = []
    for c in world.alive():
        if c.is_adult or c.age < BETROTHAL_MIN_AGE:
            continue
        if c.spouse is not None or c.betrothed is not None:
            continue
        if world.is_descendant(c.id, player_id):
            own.append(c)
        else:
            other.append(c)
    own.sort(key=lambda c: c.birth_year)
    other.sort(key=lambda c: (c.birth_year, c.dynasty or 0))
    return own, other


def ai_marriages(world: World, chance: float = 0.03) -> None:
    """NPC 自动婚配（保证家族血脉延续，避免人口雪崩）。

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
        if c.spouse is None and c.betrothed is None and c.is_adult and c.age <= MARRIAGE_MAX_AGE and c.id != world.player_id
    ]
    world.rng.shuffle(singles)
    for c in singles:
        if c.spouse is not None or c.betrothed is not None or world.rng.random() > chance:
            continue
        options = [
            o
            for o in singles
            if o.spouse is None and o.betrothed is None and o.id != c.id and o.gender != c.gender and o.id != world.player_id
        ]
        if not options:
            continue
        arrange_marriage(world, c.id, world.rng.choice(options).id)
