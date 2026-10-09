"""健康与死亡（死因 reason 传 i18n death.* 键；旧存档的中文原文兼容显示）。"""

from __future__ import annotations

from .. import balance as B
from .. import i18n
from .models import Character
from .world import World


def birth_health(world: World, gender: str) -> float:
    lo, hi = B.BIRTH_HEALTH_MALE if gender == "male" else B.BIRTH_HEALTH_FEMALE
    return world.rng.uniform(lo, hi)


def death_chance(char: Character) -> float:
    h, age = char.health, char.age
    if h < 0:
        p = 0.5
    elif h < 1:
        p = 0.25
    elif h < 3:
        p = 0.08
    elif h < 5:
        p = 0.02
    else:
        p = 0.0
    if age >= B.OLD_AGE_DEATH_AGE:
        p += (age - B.OLD_AGE_DEATH_AGE + 1) * 0.012
    return min(0.95, p)


def death_reason_label(reason: str) -> str:
    """支持旧存档原文与新版 death.* 键。"""
    label = i18n.t(f"death.{reason}")
    return label if label != f"death.{reason}" else reason


def kill(world: World, char: Character, reason: str) -> None:
    if not char.is_alive:
        return
    char.death_year = world.date.year
    char.death_reason = reason
    label = death_reason_label(reason)
    world.add_log(f"⚰ {i18n.t('event.death', name=char.name, age=char.age, reason=label)}")
    world.add_event(
        "death", "event.death", {"name": char.name, "age": char.age, "reason": label}, [char.id]
    )


def yearly_health(world: World) -> None:
    for char in world.alive():
        age = char.age
        # 儿童早夭（近似）
        if age < B.CHILDHOOD_END and world.rng.random() < B.CHILD_MORTALITY_YEARLY:
            kill(world, char, "childhood")
            continue
        # 成年人意外（近似）
        if age >= B.CHILDHOOD_END and age < B.OLD_AGE_DEATH_AGE:
            if world.rng.random() < B.ADULT_ACCIDENT_YEARLY:
                kill(world, char, "accident")
                continue
        if age >= B.HEALTH_LOSS_START_AGE:
            chance = B.HEALTH_LOSS_CHANCE + (age - B.HEALTH_LOSS_START_AGE) * B.HEALTH_LOSS_CHANCE_INCREMENT
            if world.rng.random() < chance:
                char.health -= B.HEALTH_LOSS_AMOUNT
        if age >= B.PROWESS_LOSS_START_AGE:
            chance = B.PROWESS_LOSS_CHANCE + (age - B.PROWESS_LOSS_START_AGE) * B.PROWESS_LOSS_CHANCE_INCREMENT
            if world.rng.random() < chance:
                char.attributes["prowess"] = max(0, char.attributes.get("prowess", 0) - 1)
        if world.rng.random() < B.DISEASE_YEARLY_CHANCE:
            char.health -= B.DISEASE_HEALTH_LOSS

        if world.rng.random() < death_chance(char):
            kill(world, char, "disease" if char.health < 3 else "old_age")
