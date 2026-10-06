"""特质库与数据加载。"""

from __future__ import annotations

import json
import pathlib
from functools import lru_cache
from typing import Any

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
        for level_str, display in spec["levels"].items():
            level = int(level_str)
            tid = f"{group}_{'n' if level < 0 else 'p'}{abs(level)}"
            db[tid] = {
                "name": display,
                "type": "congenital",
                "group": group,
                "level": level,
                "attrs": {a: level * spec.get("per_level_attrs", 1) for a in spec["attrs"]},
                "health": level * spec.get("per_level_health", 0.0),
                "prowess": level * spec.get("per_level_prowess", 0),
            }
    return db


TRAITS: dict[str, dict] = _build_traits()
_trait_data = load_json("traits.json")
CONGENITAL_GROUPS: dict[str, dict] = _trait_data.get("congenital_groups", {})
PERSONALITY: dict[str, dict] = _trait_data.get("personality", {})
EDUCATION: dict[str, Any] = _trait_data.get("education", {})


def trait_def(tid: str) -> dict:
    return TRAITS.get(tid, {})


def trait_name(tid: str) -> str:
    return TRAITS.get(tid, {}).get("name", tid)


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
    if not education or not education.startswith("edu_"):
        return ""
    parts = education.split("_")
    if len(parts) != 3:
        return education
    _, route, level = parts
    route_name = EDUCATION.get("routes", {}).get(route, route)
    return f"{route_name}{level}级"
