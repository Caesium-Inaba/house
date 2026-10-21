"""默认剧本：1066 年波希米亚 · 普热梅斯利德家族。

史实骨架、数值架空，主要用于验证生育与家族经营闭环。
"""

from __future__ import annotations

from typing import Optional

from .. import balance as B
from .. import i18n
from . import genetics
from . import traits as T
from .models import Character
from .world import World


# 开局史实人物生日：史料多仅存出生年份，月日为游戏采定数据（确定值，不随机）。
_SCENARIO_BIRTHDAYS: dict[str, tuple[int, int]] = {
    "弗拉季斯拉夫": (6, 15),
    "斯瓦塔瓦": (3, 2),
    "布热季斯拉夫": (2, 14),
    "尤迪塔": (9, 9),
    "博莱斯瓦夫": (1, 20),
    "阿格涅什卡": (5, 5),
    "盖佐": (4, 12),
    "伊洛娜": (7, 7),
    "韦尔夫": (11, 3),
    "玛蒂尔达": (3, 21),
    "雅罗米尔": (10, 30),
}


def _birthday(name: str) -> tuple[int, int]:
    return _SCENARIO_BIRTHDAYS.get(name, (1, 1))


def _adult(
    world: World,
    name: str,
    gender: str,
    birth_year: int,
    dynasty: Optional[int],
    attrs: dict[str, int],
    genes: Optional[dict[str, int]] = None,
    education: Optional[str] = None,
    health: float = 5.4,
    personality: Optional[set[str]] = None,
) -> Character:
    genes = dict(genes or {})
    bm, bd = _birthday(name)
    full_attrs = {k: attrs.get(k, B.ATTR_BASE) for k in B.ATTR_KEYS}
    char = Character(
        id=world.new_char_id(),
        name=name,
        gender=gender,
        birth_year=birth_year,
        birth_month=bm,
        birth_day=bd,
        dynasty=dynasty,
        genes=genes,
        education=education,
        health=health,
        traits=set(personality or []),
        potential=dict(full_attrs),
        money=world.rng.uniform(20, 60),
        prestige=world.rng.uniform(0, 40),
    )
    char.sexuality = genetics.roll_sexuality(world)
    cong = T.congenital_attr_bonus(genes)
    edu = T.education_attr_bonus(education)
    pers = T.personality_attrs(char.traits)
    for k in B.ATTR_KEYS:
        char.attributes[k] = max(B.ATTR_MIN, min(B.ATTR_MAX, full_attrs[k] + cong.get(k, 0) + edu.get(k, 0) + pers.get(k, 0)))
    world.add_character(char)
    return char


def _child(
    world: World,
    name: str,
    gender: str,
    birth_year: int,
    father: Character,
    mother: Character,
    dynasty: Optional[int],
) -> Character:
    bm, bd = _birthday(name)
    char = Character(
        id=world.new_char_id(),
        name=name,
        gender=gender,
        birth_year=birth_year,
        birth_month=bm,
        birth_day=bd,
        dynasty=dynasty,
        father=father.id,
        mother=mother.id,
        health=world.rng.uniform(4.8, 5.4),
        potential={k: B.ATTR_BASE + world.rng.randint(0, 4) for k in B.ATTR_KEYS},
    )
    char.sexuality = genetics.roll_sexuality(world)
    for k in B.ATTR_KEYS:
        char.attributes[k] = max(0, round(char.potential[k] * 0.15))
    world.add_character(char)
    father.children.append(char.id)
    mother.children.append(char.id)
    return char


def build_default_world(seed: Optional[int] = None) -> World:
    world = World()
    if seed is not None:
        world.rng.seed(seed)
    world.date.year = 1066
    world.date.month = 1
    world.date.day = 1

    premyslid = world.add_dynasty("普热梅斯利德", "czech")
    piast = world.add_dynasty("皮亚斯特", "polish")
    arpad = world.add_dynasty("阿尔帕德", "hungarian")
    welf = world.add_dynasty("韦尔夫", "german")

    # ── 主角：波希米亚公爵弗拉季斯拉夫二世 ──
    vratislav = _adult(
        world,
        "弗拉季斯拉夫",
        "male",
        1035,
        premyslid.id,
        {"diplomacy": 14, "martial": 12, "stewardship": 13, "intrigue": 10, "learning": 7, "prowess": 8},
        genes={"intellect_p2": 2},
        education="edu_diplomacy_4",
        personality={"brave", "ambitious"},
    )
    world.player_id = vratislav.id
    premyslid.head = vratislav.id
    vratislav.money = 120.0
    vratislav.prestige = 200.0

    # ── 配偶：皮亚斯特家的斯瓦塔瓦 ──
    swatawa = _adult(
        world,
        "斯瓦塔瓦",
        "female",
        1048,
        piast.id,
        {"diplomacy": 10, "martial": 5, "stewardship": 9, "intrigue": 7, "learning": 6, "prowess": 4},
        genes={"beauty_p2": 2},
        education="edu_diplomacy_2",
        personality={"generous", "diligent"},
    )
    vratislav.spouse = swatawa.id
    swatawa.spouse = vratislav.id
    vratislav.patrilineal = swatawa.patrilineal = True
    vratislav.opinions[swatawa.id] = 35
    swatawa.opinions[vratislav.id] = 35

    # ── 子嗣 ──
    _child(world, "布热季斯拉夫", "male", 1056, vratislav, swatawa, premyslid.id)
    _child(world, "尤迪塔", "female", 1058, vratislav, swatawa, premyslid.id)

    # ── 邻邦与婚配候选 ──
    _adult(world, "博莱斯瓦夫", "male", 1042, piast.id,
           {"diplomacy": 11, "martial": 13, "stewardship": 10, "intrigue": 9, "learning": 6, "prowess": 10},
           education="edu_martial_3", personality={"wroth", "brave"})
    _adult(world, "阿格涅什卡", "female", 1050, piast.id,
           {"diplomacy": 9, "martial": 4, "stewardship": 8, "intrigue": 6, "learning": 7, "prowess": 3},
           genes={"beauty_p1": 2}, education="edu_stewardship_2", personality={"patient"})

    _adult(world, "盖佐", "male", 1040, arpad.id,
           {"diplomacy": 10, "martial": 12, "stewardship": 11, "intrigue": 8, "learning": 5, "prowess": 9},
           education="edu_martial_3", personality={"generous", "brave"})
    _adult(world, "伊洛娜", "female", 1052, arpad.id,
           {"diplomacy": 11, "martial": 4, "stewardship": 7, "intrigue": 9, "learning": 8, "prowess": 3},
           education="edu_intrigue_3", personality={"deceitful", "ambitious"})

    _adult(world, "韦尔夫", "male", 1038, welf.id,
           {"diplomacy": 12, "martial": 11, "stewardship": 12, "intrigue": 7, "learning": 8, "prowess": 7},
           education="edu_stewardship_3", personality={"honest", "content"})
    _adult(world, "玛蒂尔达", "female", 1049, welf.id,
           {"diplomacy": 13, "martial": 5, "stewardship": 8, "intrigue": 8, "learning": 9, "prowess": 3},
           genes={"intellect_p1": 2}, education="edu_learning_3", personality={"diligent", "honest"})

    # ── 一位族中长老，便于日后继承/摄政 ──
    _adult(world, "雅罗米尔", "male", 1030, premyslid.id,
           {"diplomacy": 8, "martial": 9, "stewardship": 10, "intrigue": 9, "learning": 11, "prowess": 5},
           education="edu_learning_3", personality={"chaste", "content"})

    world.refresh_ages()
    start_params = {"name": vratislav.name, "dynasty": premyslid.name}
    world.add_log(f"1066年1月1日：{i18n.t('event.scenario_start', **start_params)}")
    world.add_event("succession", "event.scenario_start", start_params, [vratislav.id])
    world.head_history.append(vratislav.id)
    return world
