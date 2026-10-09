"""特质库与数据加载（显示名经 i18n，本模块只管数值与结构）。"""

from __future__ import annotations

import json
import pathlib
from functools import lru_cache
from typing import Any

from ..i18n import t as _t

_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=None)
def load_json(name: str) -> Any:
    path = _DATA_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def _build_traits() -> dict[str, dict]:
    raw = load_json("traits.json")
    db: dict[str, dict] = dict(raw.get("traits", {}))
    db.update(raw.get("personality", {}))

    # 展开等级化先天特质组：intellect_n3 / intellect_p2 ...
    for group, spec in raw.get("congenital_groups", {}).items():
        for level_str in spec["levels"]:
            level = int(level_str)
            tid = f"{group}_{'n' if level < 0 else 'p'}{abs(level)}"
            # 每级显式表（CK3 不等差）优先，否则线性
            if "levels_attrs" in spec and level_str in spec["levels_attrs"]:
                attrs = dict(spec["levels_attrs"][level_str])
            else:
                attrs = {a: level * spec.get("per_level_attrs", 1) for a in spec.get("attrs", [])}
            db[tid] = {
                "type": "congenital",
                "group": group,
                "level": level,
                "attrs": attrs,
                "health": level * spec.get("per_level_health", 0.0),
                "prowess": level * spec.get("per_level_prowess", 0),
            }
    return db


TRAITS: dict[str, dict] = _build_traits()
_trait_data = load_json("traits.json")
CONGENITAL_GROUPS: dict[str, dict] = _trait_data.get("congenital_groups", {})
PERSONALITY: dict[str, dict] = _trait_data.get("personality", {})
EDUCATION: dict[str, Any] = _trait_data.get("education", {})
CHILDHOOD: dict[str, dict] = _trait_data.get("childhood", {})
PERSONALITY_IDS: list[str] = list(PERSONALITY)


def _t(key: str, fallback: str) -> str:
    from .. import i18n

    name = i18n.t(key)
    return name if name != key else fallback


def trait_def(tid: str) -> dict:
    return TRAITS.get(tid, {})


def trait_name(tid: str) -> str:
    """显示名完全来自 i18n（data/locales/*.json），缺键时回退原 id 便于发现漏译。"""
    return _t(f"trait.{tid}", str(tid))


def is_congenital(tid: str) -> bool:
    return TRAITS.get(tid, {}).get("type") == "congenital"


def congenital_group(tid: str) -> str | None:
    return TRAITS.get(tid, {}).get("group")


def congenital_level(tid: str) -> int:
    return int(TRAITS.get(tid, {}).get("level", 0))


def all_congenital_ids() -> list[str]:
    return [tid for tid, d in TRAITS.items() if d.get("type") == "congenital"]


def all_positive_congenital() -> list[str]:
    out = []
    for tid in all_congenital_ids():
        d = TRAITS[tid]
        lvl = int(d.get("level", 0))
        if lvl > 0:
            out.append(tid)
        elif lvl == 0 and d.get("fertility", 0) > 0:  # fecund 等
            out.append(tid)
    return out


def all_negative_congenital() -> list[str]:
    out = []
    for tid in all_congenital_ids():
        d = TRAITS[tid]
        lvl = int(d.get("level", 0))
        if lvl < 0 or (lvl == 0 and d.get("health", 0) < 0):
            out.append(tid)
    return out


def congenital_attr_bonus(genes: dict[str, int]) -> dict[str, int]:
    """由激活的先天基因（state==2）得到属性加成。"""
    bonus = {k: 0 for k in ("diplomacy", "martial", "stewardship", "intrigue", "learning", "prowess")}
    for tid, state in genes.items():
        if state != 2:
            continue
        d = TRAITS.get(tid)
        if not d:
            continue
        for a, v in d.get("attrs", {}).items():
            if a in bonus:
                bonus[a] += v
        if "prowess" in d:
            bonus["prowess"] += d["prowess"]
    return bonus


def congenital_health_bonus(genes: dict[str, int]) -> float:
    bonus = 0.0
    for tid, state in genes.items():
        if state != 2:
            continue
        bonus += TRAITS.get(tid, {}).get("health", 0.0)
    return bonus


def trait_fertility_modifier(traits: set[str]) -> float:
    return sum(TRAITS.get(t, {}).get("fertility", 0.0) for t in traits)


def personality_attrs(traits: set[str]) -> dict[str, int]:
    """性格特质的属性修正（CK3：勇敢 +2 军事 等）。"""
    bonus = {k: 0 for k in ("diplomacy", "martial", "stewardship", "intrigue", "learning", "prowess")}
    for tid in traits:
        d = TRAITS.get(tid, {})
        for a, v in d.get("attrs", {}).items():
            if a in bonus:
                bonus[a] += v
        p = d.get("prowess")
        if isinstance(p, (int, float)):
            bonus["prowess"] += int(p)
    return bonus


def income_mods(traits: set[str]) -> dict[str, float]:
    """性格特质的收入修正（按人物逐个应用；月值×12 转为年值）。"""
    mods = {
        "money_pct": 0.0,
        "prestige_pct": 0.0,
        "piety_pct": 0.0,
        "prestige_flat_yearly": 0.0,
        "piety_flat_yearly": 0.0,
    }
    for tid in traits:
        d = TRAITS.get(tid, {})
        mods["money_pct"] += d.get("money_pct", 0.0)
        mods["prestige_pct"] += d.get("prestige_pct", 0.0)
        mods["piety_pct"] += d.get("piety_pct", 0.0)
        mods["prestige_flat_yearly"] += d.get("prestige_monthly", 0.0) * 12.0
        mods["piety_flat_yearly"] += d.get("piety_monthly", 0.0) * 12.0
    return mods


def opinion_delta(a_traits: set[str], b_traits: set[str]) -> int:
    """CK3 性格 → 性格好感：同特质 +10，异特质 −10（个别 −15）。取双方对称和的一半。"""
    delta = 0
    for ta in a_traits:
        da = PERSONALITY.get(ta, {})
        opp = set(da.get("opposites", []))
        for tb in b_traits:
            if tb == ta:
                delta += 10
            elif tb in opp:
                delta += da.get("opp_opinion", -10)
    return delta // 2


def education_attr_bonus(education: str | None) -> dict[str, int]:
    """教育特质 id 形如 edu_martial_3。"""
    bonus = {k: 0 for k in ("diplomacy", "martial", "stewardship", "intrigue", "learning", "prowess")}
    if not education or not education.startswith("edu_"):
        return bonus
    parts = education.split("_")
    if len(parts) != 3:
        return bonus
    _, route, level = parts
    if route in bonus:
        bonus[route] += EDUCATION.get("per_level_attrs", {}).get(level, 0)
    return bonus


def education_name(education: str | None) -> str:
    """教育特质全名（官方汉化采录），如 edu_diplomacy_4 → 幕后操控人。"""
    if not education or not education.startswith("edu_"):
        return ""
    parts = education.split("_")
    if len(parts) != 3:
        return education
    _, route, level = parts
    return _t(f"edu.{route}.{level}", education)


def education_routes() -> list[str]:
    return list(EDUCATION.get("routes", []))


# ── 童年特质（CK3：6 岁显现，隐含推定教育方向；16 岁按 converts 表转换） ──

CHILDHOOD_IDS: list[str] = [k for k in CHILDHOOD if not k.startswith("_")]


def childhood_name(tid: str) -> str:
    return _t(f"trait.{tid}", str(tid))


def childhood_focus(tid: str) -> str:
    return CHILDHOOD.get(tid, {}).get("focus", "diplomacy")


def childhood_conversion(tid: str) -> str:
    """成年时童年特质转化为的性格特质 id。"""
    return CHILDHOOD.get(tid, {}).get("converts", "")


def roll_childhood_trait(world, child) -> None:
    """为满 6 岁的孩子抽取童年特质。"""
    if child.childhood_trait is None:
        child.childhood_trait = world.rng.choice(CHILDHOOD_IDS)
