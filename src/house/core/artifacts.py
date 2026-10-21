"""宝物系统（CK3 Artifacts 精神）：定义数据 + 实例 + 装备/赠予/销毁/重铸/耐久/传承。

- 定义来自 data/artifacts.json（正式版为空；模组通过同名文件按键合并新增）；
- 实例挂在 Character.artifacts：{"uid", "def", "durability"}；
- 每个槽位最多装备一件（Character.equipped: slot -> uid），只有装备中的宝物生效；
- 耐久每年 −1，归零损毁；稀有度决定耐久/销毁返金/重铸费用（CK3 表）；
- 赠予不默认加好感；可选 gift_effect（如「忠贞的配偶」减压力）；
- 任何角色死亡时，宝物交给其第一继承人；无继承人则消失。
"""

from __future__ import annotations

from typing import Optional

from .. import balance as B
from .. import i18n
from . import traits as T
from .models import Character
from .world import World


def defs() -> dict[str, dict]:
    data = T.load_json("artifacts.json")
    return data.get("artifacts", {}) if isinstance(data, dict) else {}


def definition(def_id: str) -> Optional[dict]:
    return defs().get(def_id)


def max_durability(def_id: str) -> int:
    d = definition(def_id) or {}
    rarity = d.get("rarity", "common")
    default = B.ARTIFACT_RARITIES.get(rarity, {}).get("durability", 60)
    return int(d.get("durability", default))


def slot_of(def_id: str) -> str:
    return str((definition(def_id) or {}).get("slot", "trinket"))


def rarity_of(def_id: str) -> str:
    return str((definition(def_id) or {}).get("rarity", "common"))


def equipped_artifacts(char: Character) -> list[dict]:
    ids = set(char.equipped.values())
    return [a for a in char.artifacts if a.get("uid") in ids]


def _modifier_total(char: Character, key: str) -> float:
    total = 0.0
    for a in equipped_artifacts(char):
        d = definition(a.get("def", "")) or {}
        total += float((d.get("modifiers") or {}).get(key, 0.0))
    return total


def fertility_multiplier(char: Character) -> float:
    """装备宝物的生育力乘数（1 + 累加值，下限 0）。"""
    return max(0.0, 1.0 + _modifier_total(char, "fertility_mult"))


def health_decay_multiplier(char: Character) -> float:
    """装备宝物对「年龄健康流逝」的乘数（1 为不变）。"""
    mult = 1.0
    for a in equipped_artifacts(char):
        d = definition(a.get("def", "")) or {}
        mult *= float((d.get("modifiers") or {}).get("health_decay_mult", 1.0))
    return max(0.0, mult)


def stress_gain_multiplier(char: Character) -> float:
    """装备宝物对压力获得的乘数；可要求持有者具备某特质（如忠贞）。"""
    mult = 1.0
    for a in equipped_artifacts(char):
        d = definition(a.get("def", "")) or {}
        mods = d.get("modifiers") or {}
        value = float(mods.get("stress_gain_mult", 1.0))
        need = mods.get("stress_gain_mult_trait")
        if need and need not in char.traits:
            continue
        mult *= value
    return max(0.0, mult)


def acquire(world: World, char: Character, def_id: str) -> Optional[dict]:
    """获得一件宝物；空槽位自动装备。返回实例。"""
    if definition(def_id) is None:
        return None
    uid = world.next_artifact_uid
    world.next_artifact_uid += 1
    inst = {"uid": uid, "def": def_id, "durability": max_durability(def_id)}
    char.artifacts.append(inst)
    slot = slot_of(def_id)
    if slot not in char.equipped:
        char.equipped[slot] = uid
    params = {"name": char.name, "artifact": def_id}
    world.add_log(f"✦ {i18n.t('event.artifact_gain', **params)}")
    world.add_event("artifact", "event.artifact_gain", params, [char.id])
    return inst


def _find(char: Character, uid: int) -> Optional[dict]:
    return next((a for a in char.artifacts if a.get("uid") == uid), None)


def equip(world: World, char: Character, uid: int) -> bool:
    inst = _find(char, uid)
    if inst is None:
        return False
    char.equipped[slot_of(inst["def"])] = uid
    return True


def unequip(world: World, char: Character, uid: int) -> bool:
    for slot, value in list(char.equipped.items()):
        if value == uid:
            del char.equipped[slot]
            return True
    return False


def destroy(world: World, char: Character, uid: int) -> tuple[bool, float]:
    """销毁宝物：按定义的 destroy_gold（缺省取稀有度表）；模组宝物设为 0。"""
    inst = _find(char, uid)
    if inst is None:
        return False, 0.0
    d = definition(inst["def"]) or {}
    gold = float(d.get("destroy_gold", B.ARTIFACT_RARITIES.get(rarity_of(inst["def"]), {}).get("destroy_gold", 0)))
    char.money += gold
    char.artifacts.remove(inst)
    char.equipped = {s: u for s, u in char.equipped.items() if u != uid}
    params = {"name": char.name, "artifact": inst["def"], "gold": round(gold, 1)}
    world.add_log(f"✦ {i18n.t('event.artifact_destroy', **params)}")
    world.add_event("artifact", "event.artifact_destroy", params, [char.id])
    return True, gold


def reforge(world: World, char: Character, uid: int) -> tuple[bool, str]:
    """重铸：恢复满耐久（不可重铸的宝物拒绝）。"""
    inst = _find(char, uid)
    if inst is None:
        return False, "api.artifact_missing"
    d = definition(inst["def"]) or {}
    if not d.get("reforgeable", True):
        return False, "api.artifact_not_reforgeable"
    cost = float(B.ARTIFACT_RARITIES.get(rarity_of(inst["def"]), {}).get("reforge_cost", 100))
    if char.money < cost:
        return False, "api.artifact_cost"
    char.money -= cost
    inst["durability"] = max_durability(inst["def"])
    params = {"name": char.name, "artifact": inst["def"]}
    world.add_log(f"✦ {i18n.t('event.artifact_reforge', **params)}")
    world.add_event("artifact", "event.artifact_reforge", params, [char.id])
    return True, "api.artifact_reforged"


def can_gift(char: Character, target: Character) -> bool:
    if target.id == char.id or not target.is_alive:
        return False
    return target.dynasty == char.dynasty or target.spouse == char.id or char.spouse == target.id


def gift(world: World, char: Character, target: Character, uid: int) -> tuple[bool, str]:
    """赠予宝物；默认不增好感；gift_effect 可附加效果（如配偶减压）。"""
    inst = _find(char, uid)
    if inst is None:
        return False, "api.artifact_missing"
    if not can_gift(char, target):
        return False, "api.artifact_gift_denied"
    char.artifacts.remove(inst)
    char.equipped = {s: u for s, u in char.equipped.items() if u != uid}
    target.artifacts.append(inst)
    slot = slot_of(inst["def"])
    if slot not in target.equipped:
        target.equipped[slot] = inst["uid"]

    d = definition(inst["def"]) or {}
    effect = d.get("gift_effect") or {}
    if effect:
        need_trait = effect.get("trait")
        need_relation = effect.get("relation")
        ok = True
        if need_trait and need_trait not in target.traits:
            ok = False
        if need_relation == "spouse" and not (target.spouse == char.id or char.spouse == target.id):
            ok = False
        if ok and effect.get("stress"):
            # 赠予效果按定义值直接扣减（不走 stress_loss 修正，保证「减 5 点」足额）
            target.stress = max(0.0, target.stress - float(effect["stress"]))

    params = {"from": char.name, "to": target.name, "artifact": inst["def"]}
    world.add_log(f"✦ {i18n.t('event.artifact_gift', **params)}")
    world.add_event("artifact", "event.artifact_gift", params, [char.id, target.id])
    return True, "api.artifact_gifted"


def annual_decay(world: World) -> None:
    """每年：所有持有宝物耐久 −1，归零损毁（不返还金钱）。"""
    for char in world.alive():
        for inst in list(char.artifacts):
            inst["durability"] = int(inst.get("durability", 0)) - B.ARTIFACT_DURABILITY_YEARLY
            if inst["durability"] > 0:
                continue
            char.artifacts.remove(inst)
            char.equipped = {s: u for s, u in char.equipped.items() if u != inst["uid"]}
            params = {"name": char.name, "artifact": inst["def"]}
            world.add_log(f"✦ {i18n.t('event.artifact_broken', **params)}")
            world.add_event("artifact", "event.artifact_broken", params, [char.id])


def _close_family(world: World, a: Character, b: Character) -> bool:
    if a.spouse == b.id or b.spouse == a.id:
        return True
    if b.id in a.children or a.id in b.children:
        return True
    if a.father == b.id or a.mother == b.id or b.father == a.id or b.mother == a.id:
        return True
    # 兄弟姐妹
    if a.father is not None and a.father == b.father:
        return True
    if a.mother is not None and a.mother == b.mother:
        return True
    return False


def transfer_on_death(world: World, dead: Character) -> None:
    """死亡时宝物交给第一继承人；无继承人则消失；非近亲继承额外损失耐久。"""
    if not dead.artifacts:
        return
    from . import inheritance

    heir = inheritance.find_heir(world, dead)
    artifacts = list(dead.artifacts)
    dead.artifacts.clear()
    dead.equipped.clear()
    if heir is None:
        for inst in artifacts:
            params = {"name": dead.name, "artifact": inst["def"]}
            world.add_event("artifact", "event.artifact_lost", params, [dead.id])
        return
    stranger = not _close_family(world, dead, heir)
    for inst in artifacts:
        if stranger:
            inst["durability"] = int(inst.get("durability", 0)) - B.ARTIFACT_INHERIT_STRANGER_LOSS
        if inst["durability"] <= 0:
            params = {"name": heir.name, "artifact": inst["def"]}
            world.add_event("artifact", "event.artifact_lost", params, [heir.id])
            continue
        heir.artifacts.append(inst)
        slot = slot_of(inst["def"])
        if slot not in heir.equipped:
            heir.equipped[slot] = inst["uid"]
        params = {"name": heir.name, "artifact": inst["def"]}
        world.add_log(f"✦ {i18n.t('event.artifact_inherit', **params)}")
        world.add_event("artifact", "event.artifact_inherit", params, [heir.id, dead.id])
