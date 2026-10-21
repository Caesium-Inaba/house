"""减压决议（CK3）：数据驱动（data/decisions.json，模组可按键新增/覆盖）。

数值来源：CK3 Character_decisions#Coping_actions（应对动作 3 年 CD、减压 −20/−40）；
通用活动（狩猎/宴饮/朝圣/静修）为适配本作添加。效果字段：
stress / cost / gain / health / opinion_all / requires / cd / buy_artifact。
"""

from __future__ import annotations

from .. import i18n
from . import opinion
from . import stress
from . import traits as T
from .models import Character
from .world import World


def all_decisions() -> dict[str, dict]:
    """读取决议定义（随 traits.load_json 的缓存/模组合并自动更新）。"""
    data = T.load_json("decisions.json")
    return dict(data.get("decisions", {})) if isinstance(data, dict) else {}


def _affordable(char: Character, cost: dict) -> bool:
    for key, amount in cost.items():
        if getattr(char, key, 0.0) < amount:
            return False
    return True


def list_for(world: World, char: Character) -> list[dict]:
    """返回该角色可用的决议清单（含不可用原因）。"""
    today = world.date.ordinal()
    out = []
    for decision_id, d in all_decisions().items():
        d = dict(d, id=decision_id)
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
                "id": decision_id,
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
    d = all_decisions().get(decision_id)
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
    if d.get("buy_artifact"):
        from . import artifacts

        if artifacts.definition(d["buy_artifact"]) is None:
            return False, "api.artifact_missing"

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
    if d.get("buy_artifact"):
        from . import artifacts

        artifacts.acquire(world, char, d["buy_artifact"])
    char.decisions[decision_id] = today + d["cd"]

    params = {"name": char.name, "decision": decision_id, "stress": reduced}
    key = "event.decision" if reduced > 0 else "event.decision_plain"
    world.add_log(f"☘ {i18n.t(key, **params)}")
    world.add_event("decision", key, params, [char.id])
    return True, "api.decision_done"
