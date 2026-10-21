"""减压决议（CK3）：通用活动 + 应对机制专属动作，全部带冷却（按绝对日序号）。

数值来源：CK3 Character_decisions#Coping_actions（应对动作 3 年 CD、减压 −20/−40），
通用活动（狩猎/宴饮/朝圣/静修）为适配本作添加，冷却与花费在 balance/本文件标注采定。
"""

from __future__ import annotations

from .. import balance as B
from .. import i18n
from . import opinion
from . import stress
from .models import Character
from .world import World

# cost/gain 的键：money / prestige / piety
DECISIONS: list[dict] = [
    # ── 通用 ──
    {"id": "hunt", "group": "generic", "stress": 25, "cost": {"money": 30}, "gain": {"prestige": 10}, "cd": 365},
    {"id": "feast", "group": "generic", "stress": 40, "cost": {"money": 50, "prestige": 20}, "cd": 730},
    {"id": "pilgrimage", "group": "generic", "stress": 30, "cost": {"money": 40}, "gain": {"piety": 25}, "cd": 1095},
    {"id": "meditate", "group": "generic", "stress": 10, "cd": 180},
    # ── 应对机制（trait 解锁，3 年 CD） ──
    {"id": "coping_drink", "group": "coping", "requires": "drunkard", "stress": 20, "cost": {"prestige": 150}, "cd": 1095},
    {"id": "coping_food", "group": "coping", "requires": "comfort_eater", "stress": 20, "cost": {"money": 20}, "cd": 1095},
    {"id": "coping_seclude", "group": "coping", "requires": "reclusive", "stress": 20, "cost": {"prestige": 150}, "cd": 1095},
    {"id": "coping_confide", "group": "coping", "requires": "confider", "stress": 20, "opinion_all": -5, "cd": 1095},
    {"id": "coping_workout", "group": "coping", "requires": "athletic", "stress": 20, "opinion_all": -5, "cd": 1095},
    {"id": "coping_flagellate", "group": "coping", "requires": "flagellant", "stress": 40, "health": -0.2, "cd": 1095},
    {"id": "coping_lash_out", "group": "coping", "requires": "irritable", "stress": 20, "opinion_all": -5, "cd": 1095},
    {"id": "coping_confess", "group": "coping", "requires": "contrite", "stress": 20, "gain": {"piety": 10}, "cd": 1095},
    {"id": "coping_shun_food", "group": "coping", "requires": "inappetetic", "stress": 20, "cd": 1095},
    {"id": "coping_charity", "group": "coping", "requires": "improvident", "stress": 20, "cost": {"money": 20}, "gain": {"piety": 25}, "cd": 1095},
    {"id": "coping_brothel", "group": "coping", "requires": "rakish", "stress": 20, "cost": {"money": 25}, "cd": 1095},
    {"id": "coping_market", "group": "coping", "requires": "profligate", "stress": 20, "cd": 1095},
    {"id": "coping_journal", "group": "coping", "requires": "journaller", "stress": 20, "cd": 1095},
]

_BY_ID = {d["id"]: d for d in DECISIONS}


def _affordable(char: Character, cost: dict) -> bool:
    for key, amount in cost.items():
        if getattr(char, key, 0.0) < amount:
            return False
    return True


def list_for(world: World, char: Character) -> list[dict]:
    """返回该角色可用的决议清单（含不可用原因）。"""
    today = world.date.ordinal()
    out = []
    for d in DECISIONS:
        requires = d.get("requires")
        owned = requires is None or requires in char.traits
        ready_at = char.decisions.get(d["id"])
        cd_left = max(0, (ready_at - today)) if ready_at is not None else 0
        reason = ""
        if not owned:
            reason = "locked"
        elif cd_left > 0:
            reason = "cooldown"
        elif not _affordable(char, d.get("cost", {})):
            reason = "cost"
        out.append(
            {
                "id": d["id"],
                "group": d["group"],
                "stress": d["stress"],
                "cost": d.get("cost", {}),
                "gain": d.get("gain", {}),
                "requires": requires,
                "cd": d["cd"],
                "cd_left": cd_left,
                "available": owned and cd_left == 0 and _affordable(char, d.get("cost", {})),
                "reason": reason,
            }
        )
    return out


def apply(world: World, char: Character, decision_id: str) -> tuple[bool, str]:
    """执行决议；返回 (成功, 消息 key)。"""
    d = _BY_ID.get(decision_id)
    if d is None:
        return False, "api.unknown_decision"
    if not char.is_alive:
        return False, "api.no_living_head"
    if d.get("requires") and d["requires"] not in char.traits:
        return False, "api.decision_locked"
    today = world.date.ordinal()
    ready_at = char.decisions.get(decision_id)
    if ready_at is not None and today < ready_at:
        return False, "api.decision_cd"
    if not _affordable(char, d.get("cost", {})):
        return False, "api.decision_cost"

    for key, amount in d.get("cost", {}).items():
        setattr(char, key, getattr(char, key) - amount)
    for key, amount in d.get("gain", {}).items():
        setattr(char, key, getattr(char, key) + amount)
    if d.get("health"):
        char.health += d["health"]
    reduced = stress.reduce_stress(world, char.id, d["stress"])
    if d.get("opinion_all"):
        for other in world.alive():
            if other.id != char.id:
                opinion.add_opinion(char, other.id, d["opinion_all"])
    char.decisions[decision_id] = today + d["cd"]

    params = {"name": char.name, "decision": decision_id, "stress": reduced}
    world.add_log(f"☘ {i18n.t('event.decision', **params)}")
    world.add_event("decision", "event.decision", params, [char.id])
    return True, "api.decision_done"
