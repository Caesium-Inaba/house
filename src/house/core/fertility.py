"""生育：有效生育力、月受孕、妊娠、分娩。"""

from __future__ import annotations

from .. import balance as B
from . import genetics
from . import traits as T
from .models import Character
from .world import World


def age_multiplier(gender: str, age: int) -> float:
    if age < 16:
        return 0.0
    table = B.FERTILITY_AGE_MALE if gender == "male" else B.FERTILITY_AGE_FEMALE
    for lo, hi, mult in table:
        if lo <= age <= hi:
            return mult
    return 0.0


def fertility_value(world: World, char: Character) -> float:
    """基础生育力 + 特质修正 - 多子惩罚。"""
    v = B.FERTILITY_BASE
    v += T.trait_fertility_modifier(char.traits)
    for tid, state in char.genes.items():
        if state == 2:
            v += T.TRAITS.get(tid, {}).get("fertility", 0.0)
    if char.gender == "female":
        v -= B.FERTILITY_PER_CHILD_PENALTY * char.children_born
    return max(0.0, v)


def effective_fertility(world: World, char: Character) -> float:
    return fertility_value(world, char) * age_multiplier(char.gender, char.age)


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
    if age_multiplier("female", mother.age) <= 0:
        return False
    if mother.children_born >= B.MAX_CHILDREN_FEMALE:
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

    risk = B.CHILDBED_DEATH_BASE + max(0, mother.age - 30) * B.CHILDBED_DEATH_AGE_FACTOR
    if world.rng.random() < risk:
        from .health import kill

        kill(world, mother, "难产")
