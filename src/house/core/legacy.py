"""王朝传承（Dynasty Legacies）：威名消费的长期能力树。

5 棵树各 5 级；首级 500 威名，后级 ×1.5（wiki 社区采录，中可信度，可调）。
效果通过 family_modifiers() 聚合成家族修正，注入生育 / 健康 / 资源等公式。
"""

from __future__ import annotations

from typing import TypedDict

from .. import balance as B
from .models import Dynasty
from .world import World

TREES: list[dict] = [
    {"id": "blood", "label": "血脉", "desc": "生育与血脉延续"},
    {"id": "warfare", "label": "武略", "desc": "勇武与体魄"},
    {"id": "law", "label": "律法", "desc": "产业与秩序"},
    {"id": "guile", "label": "谋略", "desc": "谋略与心机"},
    {"id": "glory", "label": "荣光", "desc": "威望与威名"},
]

MAX_LEVEL = 5


def legacy_cost(level: int) -> int:
    """解锁 level+1 级的花费；level 为已解锁级数（0..4）。"""
    costs = [500, 750, 1125, 1700, 2500]
    return costs[min(level, MAX_LEVEL - 1)]


def level_of(dynasty: Dynasty, tree: str) -> int:
    return int(dynasty.legacies.get(tree, 0))


class FamilyMods(TypedDict):
    fertility_mult: float
    health_add: float
    prowess_add: int
    intrigue_add: int
    fert_age_offset: int
    inbreeding_resist: float
    money_mult: float
    prestige_mult: float


def family_modifiers(world: World, dynasty_id: int | None) -> "FamilyMods":
    """把传承树效果聚合为家族修正（各树取已解锁最高级）。"""
    dyn = world.dynasties.get(dynasty_id) if dynasty_id is not None else None
    m = FamilyMods(
        fertility_mult=0.0,
        health_add=0.0,
        prowess_add=0,
        intrigue_add=0,
        fert_age_offset=0,
        inbreeding_resist=0.0,
        money_mult=0.0,
        prestige_mult=0.0,
    )
    if dyn is None:
        return m
    blood = level_of(dyn, "blood")
    warfare = level_of(dyn, "warfare")
    law = level_of(dyn, "law")
    guile = level_of(dyn, "guile")
    glory = level_of(dyn, "glory")
    # 血脉：CK3 首级 +10% 生育力；后续扩展近交抗性/健康
    if blood >= 1:
        m["fertility_mult"] += 0.10
    if blood >= 2:
        m["fertility_mult"] += 0.05
    if blood >= 3:
        m["health_add"] += 0.5
    if blood >= 4:
        m["fert_age_offset"] += 5
    if blood >= 5:
        m["inbreeding_resist"] += 0.25
    # 武略：家族勇武与健康（无战争系统的适配映射）
    m["prowess_add"] += warfare
    m["health_add"] += 0.25 * warfare
    # 律法：产业（适配：金钱收入 +5%/级）
    m["money_mult"] += 0.05 * law
    # 谋略：家族谋略 +1/级
    m["intrigue_add"] = guile
    # 荣光：威望产出 +5%/级
    m["prestige_mult"] += 0.05 * glory
    return m


def can_buy(world: World, dynasty_id: int, tree: str) -> tuple[bool, str, int]:
    """能否解锁下一级：返回 (允许, 原因, 花费)。"""
    dyn = world.dynasties.get(dynasty_id)
    if dyn is None:
        return False, "没有王朝", 0
    tree_ids = {t["id"] for t in TREES}
    if tree not in tree_ids:
        return False, "未知传承树", 0
    cur = level_of(dyn, tree)
    if cur >= MAX_LEVEL:
        return False, "该传承树已满级", 0
    cost = legacy_cost(cur)
    if dyn.renown < cost:
        return False, f"威名不足（需 {cost}）", cost
    return True, "", cost


def buy(world: World, dynasty_id: int, tree: str) -> tuple[bool, str]:
    ok, msg, cost = can_buy(world, dynasty_id, tree)
    if not ok:
        return False, msg
    dyn = world.dynasties[dynasty_id]
    dyn.renown -= cost
    dyn.legacies[tree] = level_of(dyn, tree) + 1
    world.add_log(f"✦ 王朝解锁传承：{next(t['label'] for t in TREES if t['id'] == tree)} 第 {dyn.legacies[tree]} 级。")
    world.add_event("legacy", f"王朝解锁传承：{next(t['label'] for t in TREES if t['id'] == tree)} 第 {dyn.legacies[tree]} 级。")
    return True, f"传承已解锁（-{cost} 威名）"
