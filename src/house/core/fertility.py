"""生育：有效生育力、月受孕、妊娠、分娩（数值锚定 CK3）。"""

from __future__ import annotations

from .. import balance as B
from . import genetics
from . import legacy
from . import traits as T
from .models import Character
from .world import World


def age_multiplier(world: World, char: Character) -> float:
    age = char.age
    extra_age_offset = 0
    # 多产（Fecund，CK3）：生育衰减起点 +5 岁
    if char.genes.get("fecund", 0) == 2:
        extra_age_offset += B.FERTILITY_DECAY_OFFSET_FECUND
    # 家族传承·血脉第四级：衰减起点 +5
    fm = legacy.family_modifiers(world, char.dynasty)
    extra_age_offset += fm.get("fert_age_offset", 0)
    if extra_age_offset and age >= 16:
        age += extra_age_offset
    table = B.FERTILITY_AGE_MALE if char.gender == "male" else B.FERTILITY_AGE_FEMALE
    for lo, hi, mult in table:
        if lo <= age <= hi:
            return mult
    return 0.0


def fertility_value(world: World, char: Character) -> float:
    """基础生育力 + 特质修正 - 多子惩罚（CK3 叠乘结构保留在 chance 计算里）。"""
    v = B.FERTILITY_BASE
    v += T.trait_fertility_modifier(char.traits)
    for tid, state in char.genes.items():
        if state == 2:
            v += T.TRAITS.get(tid, {}).get("fertility", 0.0)
    if char.gender == "female":
        v -= B.FERTILITY_PER_CHILD_PENALTY * char.children_born
    return max(0.0, v)


def effective_fertility(world: World, char: Character) -> float:
    fm = legacy.family_modifiers(world, char.dynasty)
    return fertility_value(world, char) * age_multiplier(world, char) * (1.0 + fm.get("fertility_mult", 0.0))


def population_factor(world: World) -> float:
    """世界规模节流：仅作用于非玩家夫妻，避免封闭小世界人口指数爆炸。"""
    alive = len(world.alive())
    if alive <= B.WORLD_SOFT_CAP:
        return 1.0
    if alive >= B.WORLD_HARD_CAP:
        return 0.05
    return max(0.05, 1.0 - (alive - B.WORLD_SOFT_CAP) / (B.WORLD_HARD_CAP - B.WORLD_SOFT_CAP))


def monthly_conception_chance(world: World, father: Character, mother: Character) -> float:
    ff = effective_fertility(world, father)
    mf = effective_fertility(world, mother)
    avg = (ff + mf) / 2
    if not (world.is_ruler(father) or world.is_ruler(mother)):
        avg = max(0.0, avg - B.FERTILITY_NON_RULER_PENALTY)
    chance = avg * B.FERTILITY_CHANCE_MULTIPLIER / 100.0
    if father.id != world.player_id and mother.id != world.player_id:
        chance *= population_factor(world)
    return chance


def _can_conceive(world: World, mother: Character) -> bool:
    if not mother.is_alive or mother.gender != "female" or mother.age < 16:
        return False
    if age_multiplier(world, mother) <= 0:
        return False
    if mother.children_born >= B.MAX_CHILDREN_FEMALE:
        return False
    if mother.spouse is not None:
        # CK3：男性存活子女上限 9（每额外配偶 +2，当前单配偶制下 extra=0，留待多配偶）
        father = world.get(mother.spouse)
        if father is not None:
            alive_kids = sum(1 for cid in father.children if world.get(cid) and world.get(cid).is_alive)
            extra_consorts = max(0, 0)  # 婚制为单配偶；若将来允许多配偶在此计额外人数
            allowed = B.MAX_CHILDREN_MALE_BASE + B.MALE_CHILDREN_PER_EXTRA_CONSORT * extra_consorts
            if alive_kids >= allowed:
                return False
    return not mother.is_pregnant


def monthly_settlement(world: World) -> None:
    for mother in list(world.characters.values()):
        if mother.gender != "female" or not mother.is_alive or mother.age < 16:
            continue
        if mother.is_pregnant:
            mother.pregnancy_months -= 1
            if mother.pregnancy_months <= 0:
                childbirth(world, mother)
            continue
        if not _can_conceive(world, mother):
            continue
        father = world.get(mother.spouse)
        if father is None or not father.is_alive or father.age < 16:
            continue
        if world.rng.random() < monthly_conception_chance(world, father, mother):
            mother.pregnancy_months = B.PREGNANCY_MONTHS
            mother.pregnancy_father = father.id
            dyn = world.dynasty_name_of(father.id)
            world.add_log(f"♡ {mother.name} 有了身孕（{dyn}）。")
            world.add_event("pregnancy", f"{mother.name} 有了身孕（{dyn}）。", [mother.id, father.id])


def _childbed_risk(mother: Character) -> float:
    """分娩死亡风险（CK3 规则定性 + 适配曲线）：基础 + 年龄，乘健康档与产次档。"""
    risk = B.CHILDBED_DEATH_BASE + max(0, mother.age - 30) * B.CHILDBED_DEATH_AGE_FACTOR
    for lo, mult in B.CHILDBED_HEALTH_MULT:
        if mother.health >= lo:
            risk *= mult
            break
    for born, mult in B.CHILDBED_EXP_MULT:
        if mother.children_born >= born:
            risk *= mult
            break
    return min(0.95, risk)


def childbirth(world: World, mother: Character) -> None:
    father_id = mother.pregnancy_father
    mother.pregnancy_months = None
    mother.pregnancy_father = None
    mother.children_born += 1

    kids = [genetics.create_child(world, father_id, mother.id, mother.patrilineal)]
    if world.rng.random() < B.TWIN_CHANCE:
        kids.append(genetics.create_child(world, father_id, mother.id, mother.patrilineal))
        mother.children_born += 1

    names = "、".join(k.name for k in kids)
    world.add_log(f"👶 {mother.name} 诞下 {names}。")
    world.add_event(
        "birth",
        f"{mother.name} 诞下 {names}。",
        [mother.id] + [k.id for k in kids],
    )

    for k in kids:
        if world.is_descendant(k.id, world.player_id):
            world.naming_queue.append({"child_id": k.id, "suggested": k.name})

    if world.rng.random() < _childbed_risk(mother):
        from .health import kill

        kill(world, mother, "难产")
