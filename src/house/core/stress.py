"""压力系统（CK3 1.20 数值）：0–400、三档惩罚、精神崩溃与应对机制。

数据来源：CK3 wiki Attributes#Stress / Traits#Coping_mechanisms /
Character_decisions#Coping_actions；`minor_stress_gain = 20` 为 wiki 脚本值原文，
其余未列明数值在 balance.py 里标注「采定」。

设计：
- 所有压力增减都过特质修正：获得 ×(1+Σstress_gain)，缓解 ×(1+Σstress_loss)；
- 首次跨 100/200/300 触发精神崩溃（5 年 CD）；400 时强制三级崩溃并清 100 压力；
- 玩家及其血亲的崩溃入队等待玩家选择（事件浮窗），AI 崩溃自动选第一个选项；
- 崩溃选项「选特质并减压」或「咬牙硬撑再涨压力」；
- 应对机制最多 2 个；全部 +20% 减压并解锁专属决议（决议见 core/decisions.py）。
"""

from __future__ import annotations

from typing import Optional

from .. import balance as B
from .. import i18n
from . import traits as T
from .models import Character
from .world import World

TIER_KEYS = ("calm", "tense", "fraying", "broken")


def tier(stress_value: int) -> int:
    level = 0
    for i, threshold in enumerate(B.STRESS_TIER_THRESHOLDS, 1):
        if stress_value >= threshold:
            level = i
    return level


def tier_key(char: Character) -> str:
    return TIER_KEYS[tier(char.stress)]


def fertility_multiplier(char: Character) -> float:
    return B.STRESS_FERTILITY_MULT[tier(char.stress)]


def health_penalty(char: Character) -> float:
    return B.STRESS_HEALTH_PENALTY[tier(char.stress)]


def coping_traits(char: Character) -> list[str]:
    return [tid for tid in char.traits if tid in T.COPING_IDS]


def gain_multiplier(char: Character) -> float:
    total = sum(T.TRAITS.get(tid, {}).get("stress_gain", 0.0) for tid in char.traits)
    return max(0.25, 1.0 + total)


def loss_multiplier(char: Character) -> float:
    total = sum(T.TRAITS.get(tid, {}).get("stress_loss", 0.0) for tid in char.traits)
    return max(0.25, 1.0 + total)


def add_stress(world: World, char_id: Optional[int], amount: float, reason: str = "") -> None:
    """统一压力入口：按特质修正增加，触发跨档崩溃判定。"""
    char = world.get(char_id)
    if char is None or not char.is_alive or amount <= 0:
        return
    before = char.stress
    gain = int(round(amount * gain_multiplier(char)))
    char.stress = min(B.STRESS_MAX, char.stress + gain)

    # 400：强制三级崩溃并清 100 压力
    if char.stress >= B.STRESS_MAX:
        char.stress = max(0, B.STRESS_MAX - 100)
        _start_break(world, char, 3, reason)
        return

    # 首次跨档（取跨过的最高档）
    crossed = 0
    for level, threshold in enumerate(B.STRESS_TIER_THRESHOLDS, 1):
        if before < threshold <= char.stress:
            crossed = level
    if crossed and _may_break(world, char):
        _start_break(world, char, crossed, reason)


def reduce_stress(world: World, char_id: Optional[int], amount: float) -> int:
    """减压（应用 stress_loss 修正），返回实际减少量。"""
    char = world.get(char_id)
    if char is None or amount <= 0:
        return 0
    loss = int(round(amount * loss_multiplier(char)))
    old = char.stress
    char.stress = max(0, char.stress - loss)
    return old - char.stress


def _may_break(world: World, char: Character) -> bool:
    if char.last_break_ordinal is None:
        return True
    return world.date.ordinal() - char.last_break_ordinal >= B.STRESS_BREAK_COOLDOWN_DAYS


def _break_options(world: World, char: Character, level: int) -> list[str]:
    own = set(char.traits)
    pool: list[str] = []
    if len(coping_traits(char)) < B.MAX_COPING_TRAITS:
        pool += [tid for tid in T.COPING_IDS if tid not in own]
    if level >= 2:
        pool += [tid for tid in ("melancholic", "eccentric") if tid not in own]
    if level >= 3:
        pool += [tid for tid in ("lunatic",) if tid not in own]
    # 兜底：用其它非性格特质补足（理论上不会走到）
    if len(pool) < 2:
        pool += [
            tid for tid in T.TRAITS
            if tid not in own and tid not in T.PERSONALITY and tid not in pool
        ]
    if len(pool) > 2:
        return world.rng.sample(pool, 2)
    return pool


def _is_player_kin(world: World, char: Character) -> bool:
    return char.id == world.player_id or world.is_descendant(char.id, world.player_id)


def _start_break(world: World, char: Character, level: int, reason: str = "") -> None:
    options = _break_options(world, char, level)
    if _is_player_kin(world, char):
        if any(e.get("char_id") == char.id for e in world.stress_queue):
            return
        world.stress_queue.append(
            world.stamp_due(
                {"char_id": char.id, "level": level, "options": options, "reason": reason}
            )
        )
        params = {"name": char.name, "level": level}
        world.add_log(f"⚡ {i18n.t('event.stress_break', **params)}")
        world.add_event("stress", "event.stress_break", params, [char.id])
    else:
        # AI 自动选择：优先应对机制（第一个可选项）
        choose = options[0] if options else None
        apply_break_choice(world, char, choose)


def apply_break_choice(world: World, char: Character, trait_id: Optional[str]) -> None:
    """落定精神崩溃：trait_id 为空 = 咬牙硬撑（再涨压力）。"""
    if trait_id:
        if trait_id not in char.traits and trait_id in T.TRAITS:
            char.traits.add(trait_id)
        reduce_stress(world, char.id, B.STRESS_BREAK_LOSS)
        params = {"name": char.name, "trait": trait_id}
        world.add_log(f"⚡ {i18n.t('event.stress_trait', **params)}")
        world.add_event("stress", "event.stress_trait", params, [char.id])
    else:
        params = {"name": char.name}
        world.add_log(f"⚡ {i18n.t('event.stress_endure', **params)}")
        world.add_event("stress", "event.stress_endure", params, [char.id])
        char.stress = min(B.STRESS_MAX - 1, char.stress)
        add_stress(world, char.id, B.STRESS_ENDURE_GAIN, "stress.reason.endure")
    char.last_break_ordinal = world.date.ordinal()
    world.stress_queue = [e for e in world.stress_queue if e.get("char_id") != char.id]


def _siblings(a: Character, b: Character) -> bool:
    if a.father is not None and a.father == b.father:
        return True
    if a.mother is not None and a.mother == b.mother:
        return True
    return False


def _grandparent(world: World, a: Character, b: Character) -> bool:
    for pid in (a.father, a.mother):
        parent = world.get(pid)
        if parent is None:
            continue
        if parent.father == b.id or parent.mother == b.id:
            return True
    return False


def grief_on_death(world: World, dead: Character) -> None:
    """血亲死亡带来的压力（配偶/子女/父母 30，兄弟姐妹 20，祖孙 15）。"""
    for c in world.alive():
        if c.id == dead.id:
            continue
        if c.spouse == dead.id or dead.id in c.children or c.father == dead.id or c.mother == dead.id:
            amount = B.GRIEF_STRESS_SPOUSE_CHILD_PARENT
        elif _siblings(c, dead):
            amount = B.GRIEF_STRESS_SIBLING
        elif _grandparent(world, c, dead) or _grandparent(world, dead, c):
            amount = B.GRIEF_STRESS_GRANDPARENT
        else:
            continue
        add_stress(world, c.id, amount, "stress.reason.grief")


def resolve_pending(world: World, char_id: int, trait_id: Optional[str]) -> bool:
    """玩家对崩溃事件的选择；trait_id 必须属于该事件的候选。"""
    entry = next((e for e in world.stress_queue if e.get("char_id") == char_id), None)
    if entry is None:
        return False
    if trait_id is not None and trait_id not in entry.get("options", []):
        return False
    char = world.get(char_id)
    if char is None or not char.is_alive:
        world.stress_queue = [e for e in world.stress_queue if e.get("char_id") != char_id]
        return False
    apply_break_choice(world, char, trait_id)
    return True
