"""快照适配层：core World -> WebUI 前端渲染所需的 JSON。

前后端的唯一边界：年龄、健康档位、关系称谓、候选人、命名建议等
所有展示逻辑都在这里算好，前端不复制核心规则。
core 演进时只需改本文件。
"""

from __future__ import annotations

import random
from typing import Any, Optional

from .. import balance as B
from ..core import inheritance, marriage
from ..core import traits as T
from ..core.models import Character
from ..core.world import World

CULTURE_LABELS: dict[str, str] = {
    "czech": "波希米亚",
    "polish": "波兰",
    "hungarian": "匈牙利",
    "german": "德意志",
}

GENDER_LAW_LABELS: dict[str, str] = {
    "male_preference": "男系优先",
    "equal": "平等继承",
    "female_preference": "女系优先",
}

HEALTH_BAR_MAX = 8.0  # 健康条归一化上限（出生约 5，极佳档 7+）


def _culture_of(world: World, dynasty_id: Optional[int]) -> str:
    dyn = world.dynasties.get(dynasty_id) if dynasty_id is not None else None
    return dyn.culture if dyn else "czech"


def _gene_polarity(tid: str) -> str:
    d = T.TRAITS.get(tid, {})
    level = int(d.get("level", 0))
    if level > 0:
        return "positive"
    if level < 0:
        return "negative"
    score = (
        d.get("fertility", 0.0)
        + d.get("health", 0.0) * 4
        + d.get("prowess", 0)
        + sum(v for v in d.get("attrs", {}).values() if isinstance(v, (int, float)))
    )
    return "positive" if score > 0 else "negative" if score < 0 else "neutral"


def _relation(world: World, player: Character, char: Character) -> Optional[str]:
    """char 相对玩家（家主）的称谓，无直接关系返回 None。"""
    if char.id == player.id:
        return "自己"
    if char.spouse == player.id:
        return "丈夫" if char.gender == "male" else "妻子"
    if char.father == player.id or char.mother == player.id:
        return "儿子" if char.gender == "male" else "女儿"
    for cid in player.children:
        parent = world.get(cid)
        if parent is None:
            continue
        if char.father == parent.id:
            return "孙子" if char.gender == "male" else "孙女"
        if char.mother == parent.id:
            return "外孙" if char.gender == "male" else "外孙女"
    if world.is_descendant(char.id, player.id):
        return "后代"
    return None


def enrich_character(world: World, char: Character, player: Optional[Character]) -> dict:
    alive = char.is_alive
    genes = []
    for tid, state in char.genes.items():
        if state < 1:
            continue
        d = T.TRAITS.get(tid, {})
        genes.append(
            {
                "id": tid,
                "name": d.get("name", tid),
                "state": state,  # 1 隐性携带 / 2 显性
                "group": d.get("group"),
                "level": d.get("level", 0),
                "polarity": _gene_polarity(tid),
            }
        )
    genes.sort(key=lambda g: (g["state"], g["id"]))

    traits = [
        {"id": tid, "name": T.trait_name(tid), "polarity": "neutral"}
        for tid in sorted(char.traits)
    ]

    opinions = sorted(char.opinions.items(), key=lambda kv: kv[1], reverse=True)
    top_opinions = [
        {"id": oid, "name": world.name_of(oid), "value": val}
        for oid, val in opinions[:6]
        if world.get(oid) is not None
    ]

    edu = T.education_name(char.education)
    health_norm = max(0.0, min(1.0, char.health / HEALTH_BAR_MAX))

    out: dict[str, Any] = {
        "id": char.id,
        "name": char.name,
        "gender": char.gender,
        "birth_year": char.birth_year,
        "death_year": char.death_year,
        "death_reason": char.death_reason,
        "alive": alive,
        "age": char.age,
        "is_adult": char.is_adult,
        "dynasty": char.dynasty,
        "father": char.father,
        "mother": char.mother,
        "spouse": char.spouse,
        "patrilineal": char.patrilineal,
        "children": list(char.children),
        "attributes": dict(char.attributes),
        "potential": dict(char.potential),
        "genes": genes,
        "traits": traits,
        "education": char.education,
        "education_name": edu,
        "health": round(char.health, 2),
        "health_tier": char.health_tier if alive else None,
        "health_norm": round(health_norm, 3),
        "money": round(char.money, 1),
        "prestige": round(char.prestige, 1),
        "piety": round(char.piety, 1),
        "opinions": top_opinions,
        "children_born": char.children_born,
        "pregnant": char.is_pregnant,
        "pregnancy_months_left": char.pregnancy_months if char.is_pregnant else None,
    }
    if player is not None:
        out["relation"] = _relation(world, player, char)
        dyn = world.dynasties.get(char.dynasty) if char.dynasty is not None else None
        out["culture"] = dyn.culture if dyn else "czech"
        out["culture_label"] = CULTURE_LABELS.get(out["culture"], out["culture"])
    return out


def _naming_entries(world: World) -> list[dict]:
    out = []
    for entry in world.naming_queue:
        child = world.get(entry.get("child_id"))
        if child is None:
            continue
        culture = _culture_of(world, child.dynasty)
        pool = T.load_json("names.json").get("cultures", {}).get(culture, {})
        names = pool.get("male" if child.gender == "male" else "female", [])
        # 仅 UI 展示用随机：独立种子，不触碰游戏 rng，保证读档复现
        ui_rng = random.Random(f"naming-{child.id}")
        suggestions = [n for n in ui_rng.sample(names, min(8, len(names))) if n != child.name]
        relation = None
        player = world.player
        if player is not None:
            relation = _relation(world, player, child)
        out.append(
            {
                "child_id": child.id,
                "suggested": entry.get("suggested", child.name),
                "child_name": child.name,
                "gender": child.gender,
                "culture": culture,
                "culture_label": CULTURE_LABELS.get(culture, culture),
                "relation": relation or "后代",
                "suggestions": suggestions,
            }
        )
    return out


def _generations(world: World) -> int:
    memo: dict[int, int] = {}

    def depth(cid: int) -> int:
        if cid in memo:
            return memo[cid]
        memo[cid] = 0  # 先占位防环
        c = world.get(cid)
        if c is None or (c.father is None and c.mother is None):
            memo[cid] = 0
            return memo[cid]
        parents = [p for p in (c.father, c.mother) if p is not None and p in world.characters]
        memo[cid] = (max(depth(p) for p in parents) + 1) if parents else 0
        return memo[cid]

    for cid in world.characters:
        depth(cid)
    return max(memo.values(), default=0) + 1


def _dynasties(world: World) -> list[dict]:
    out = []
    for dyn in world.dynasties.values():
        alive_members = [cid for cid in dyn.members if world.get(cid) is not None and world.get(cid).is_alive]
        head = world.get(dyn.head)
        out.append(
            {
                "id": dyn.id,
                "name": dyn.name,
                "culture": dyn.culture,
                "culture_label": CULTURE_LABELS.get(dyn.culture, dyn.culture),
                "head": dyn.head,
                "head_name": head.name if head else None,
                "renown": round(dyn.renown, 1),
                "members": len(dyn.members),
                "alive_members": len(alive_members),
            }
        )
    out.sort(key=lambda d: -d["renown"])
    return out


def marriage_candidate_list(world: World, char_id: int) -> list[dict]:
    player = world.get(char_id)
    out = []
    for c in marriage.candidates(world, char_id):
        out.append(enrich_character(world, c, player))
    return out


def build_snapshot(world: World) -> dict:
    player = world.player
    alive = world.alive()
    heir = inheritance.find_heir(world, player) if player is not None and player.is_alive else None
    date = world.date
    return {
        "date": {
            "year": date.year,
            "month": date.month,
            "xun": date.xun,
            "label": f"{date.year}年 {date.month}月 {B.XUN_NAMES[date.xun]}",
        },
        "player_id": world.player_id,
        "over": world.over,
        "over_reason": world.over_reason,
        "gender_law": world.gender_law,
        "gender_law_label": GENDER_LAW_LABELS.get(world.gender_law, world.gender_law),
        "characters": [enrich_character(world, c, player) for c in world.characters.values()],
        "dynasties": _dynasties(world),
        "events": list(world.events),
        "naming_queue": _naming_entries(world),
        "population": {
            "alive": len(alive),
            "total": len(world.characters),
            "soft_cap": B.WORLD_SOFT_CAP,
            "hard_cap": B.WORLD_HARD_CAP,
        },
        "heir": enrich_character(world, heir, player) if heir is not None else None,
        "stats": {
            "start_year": B.START_YEAR,
            "years_played": max(0, date.year - B.START_YEAR),
            "generations": _generations(world),
            "births": sum(1 for c in world.characters.values() if c.father is not None or c.mother is not None),
            "deaths": sum(1 for c in world.characters.values() if not c.is_alive),
            "marriages": sum(1 for e in world.events if e.get("type") == "marriage"),
        },
        "meta": {
            "attrs": [{"key": k, "label": v} for k, v in B.ATTRS.items()],
            "xun_names": list(B.XUN_NAMES),
            "health_tiers": [
                {"floor": None if f == float("-inf") else f, "label": n} for f, n in B.HEALTH_TIERS
            ],
            "consort_limit": B.CONSORT_LIMIT,
            "start_year": B.START_YEAR,
            "cultures": CULTURE_LABELS,
            "gender_laws": GENDER_LAW_LABELS,
        },
    }
