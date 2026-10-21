"""健康与死亡（死因 reason 传 i18n death.* 键；旧存档的中文原文兼容显示）。"""

from __future__ import annotations

from .. import balance as B
from .. import i18n
from . import artifacts
from . import stress
from .models import Character
from .world import World


def birth_health(world: World, gender: str) -> float:
    lo, hi = B.BIRTH_HEALTH_MALE if gender == "male" else B.BIRTH_HEALTH_FEMALE
    return world.rng.uniform(lo, hi)


def death_chance(char: Character) -> float:
    h = char.health + stress.health_penalty(char)  # 压力档位的健康惩罚计入死亡判定
    age = char.age
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
        "death", "event.death", {"name": char.name, "age": char.age, "reason": reason}, [char.id]
    )
    stress.grief_on_death(world, char)
    # 监护人离世：不再保留任何指向他的监护关系
    for other in world.alive():
        if other.guardian == char.id:
            other.guardian = None
    # 宝物交给第一继承人（无继承人则消失）
    artifacts.transfer_on_death(world, char)


def annual_person(world: World, char: Character) -> None:
    """生日当天的个人年度结算：早夭/意外/健康与勇武衰减/疾病/死亡判定。"""
    age = char.age
    # 儿童早夭（近似）
    if age < B.CHILDHOOD_END and world.rng.random() < B.CHILD_MORTALITY_YEARLY:
        kill(world, char, "childhood")
        return
    # 成年人意外（近似）
    if B.CHILDHOOD_END <= age < B.OLD_AGE_DEATH_AGE:
        if world.rng.random() < B.ADULT_ACCIDENT_YEARLY:
            kill(world, char, "accident")
            return
    if age >= B.HEALTH_LOSS_START_AGE:
        chance = B.HEALTH_LOSS_CHANCE + (age - B.HEALTH_LOSS_START_AGE) * B.HEALTH_LOSS_CHANCE_INCREMENT
        if world.rng.random() < chance:
            char.health -= B.HEALTH_LOSS_AMOUNT * artifacts.health_decay_multiplier(char)
    if age >= B.PROWESS_LOSS_START_AGE:
        chance = B.PROWESS_LOSS_CHANCE + (age - B.PROWESS_LOSS_START_AGE) * B.PROWESS_LOSS_CHANCE_INCREMENT
        if world.rng.random() < chance:
            char.attributes["prowess"] = max(0, char.attributes.get("prowess", 0) - 1)
    if world.rng.random() < B.DISEASE_YEARLY_CHANCE:
        char.health -= B.DISEASE_HEALTH_LOSS

    if world.rng.random() < death_chance(char):
        kill(world, char, "disease" if char.health < 3 else "old_age")
