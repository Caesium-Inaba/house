"""快照适配层：core World -> WebUI 前端渲染所需的 JSON。

前后端的唯一边界：年龄、健康档位、关系称谓、候选人、命名建议等
所有展示逻辑都在这里算好，前端不复制核心规则。
所有面向玩家的文案经 i18n（data/locales/*.json）；core 演进时只需改本文件。
"""

from __future__ import annotations

import random
from typing import Any, Optional

from .. import balance as B
from .. import i18n
from ..core import genetics, inheritance, legacy, marriage
from ..core import traits as T
from ..core.health import death_reason_label
from ..core.models import Character
from ..core.world import World

# 健康阈值 -> i18n 档位键（与 balance.HEALTH_TIERS 同界）
HEALTH_TIER_KEYS: list[tuple[float, str]] = [
    (float("-inf"), "dying"), (0.0, "near_death"), (1.0, "poor"),
    (3.0, "fine"), (5.0, "good"), (7.0, "excellent"),
]


def health_tier_key(health: float) -> str:
    key = "dying"
    for floor, k in HEALTH_TIER_KEYS:
        if health >= floor:
            key = k
    return key


def to_roman(n: int) -> str:
    """1..3999 的罗马数字（几世展示用）。"""
    table = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
        (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ]
    out = []
    for value, symbol in table:
        while n >= value:
            out.append(symbol)
            n -= value
    return "".join(out) or "I"


def display_name(world: World, char: Character) -> str:
    """人物展示名：世数只数「做过家主」者 —— 同名历代家主按继位顺序给罗马数字。

    - 未做过家主的人物不标世数。
    - 同名同宗不同时为家主的旁支不计数（因此后世可能比前世更大，如继到旁支）。
    - 展示为「名字II」形式（不带「世」字）。
    """
    history = world.head_history
    if char.id not in history:
        return char.name
    rank = 1
    for pid in history:
        if pid == char.id:
            break
        p = world.get(pid)
        if p is not None and p.name == char.name:
            rank += 1
    if rank < 2:
        return char.name
    return f"{char.name}{to_roman(rank)}"

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
    """char 相对玩家（家主）的称谓（i18n key），无直接关系返回 None。"""
    if char.id == player.id:
        return i18n.t("relation.self")
    if char.spouse == player.id:
        return i18n.t("relation.husband" if char.gender == "male" else "relation.wife")
    if char.father == player.id or char.mother == player.id:
        return i18n.t("relation.son" if char.gender == "male" else "relation.daughter")
    for cid in player.children:
        parent = world.get(cid)
        if parent is None:
            continue
        if char.father == parent.id:
            return i18n.t("relation.grandson" if char.gender == "male" else "relation.granddaughter")
        if char.mother == parent.id:
            return i18n.t(
                "relation.grandson_maternal" if char.gender == "male" else "relation.granddaughter_maternal"
            )
    if world.is_descendant(char.id, player.id):
        return i18n.t("relation.descendant")
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
                "name": T.trait_name(tid),
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
        {"id": oid, "name": display_name(world, world.get(oid)), "value": val}
        for oid, val in opinions[:6]
        if world.get(oid) is not None
    ]

    edu = T.education_name(char.education)
    health_norm = max(0.0, min(1.0, char.health / HEALTH_BAR_MAX))

    out: dict[str, Any] = {
        "id": char.id,
        "name": char.name,
        "display_name": display_name(world, char),
        "gender": char.gender,
        "birth_year": char.birth_year,
        "death_year": char.death_year,
        "death_reason": char.death_reason,
        "death_reason_label": death_reason_label(char.death_reason) if char.death_reason else None,
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
        "health_tier": health_tier_key(char.health) if alive else None,
        "health_tier_label": i18n.t(f"health.tier.{health_tier_key(char.health)}") if alive else None,
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
        out["culture_label"] = i18n.t(f"culture.{out['culture']}")

    # ── 教养 / 婚约（CK3） ──
    focus = char.education_focus
    bd = world.get(char.betrothed)
    out["childhood_trait"] = (
        {"id": char.childhood_trait, "name": T.childhood_name(char.childhood_trait),
         "focus": T.childhood_focus(char.childhood_trait)}
        if char.childhood_trait else None
    )
    out["education_focus"] = focus
    out["education_focus_label"] = i18n.t(f"attr.{focus}") if focus else None
    out["education_score"] = char.education_score
    guardian = world.get(char.guardian)
    out["guardian"] = guardian.id if guardian else None
    out["guardian_name"] = display_name(world, guardian) if guardian else None
    out["betrothed"] = (
        {"id": char.betrothed, "name": display_name(world, bd) if bd else None,
         "patrilineal": not any(
             e.get("patrilineal") is False and char.id in (e.get("a"), e.get("b"))
             for e in world.betrothals
         )}
        if char.betrothed else None
    )
    out["sexuality"] = char.sexuality
    out["sexuality_label"] = i18n.t(f"sexuality.{char.sexuality}")
    if player is not None:
        out["opinion_of_player"] = char.opinions.get(player.id)  # 被看人 → 家主
        out["player_opinion"] = player.opinions.get(char.id)      # 家主 → 被看人
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
        # 推荐名避开同父/同母手足（含已故）；手动输入不受约束（同名走「二世」）
        used_by_siblings: set[str] = set()
        for pid in (child.father, child.mother):
            parent = world.get(pid)
            if parent is None:
                continue
            for cid in parent.children:
                sib = world.get(cid)
                if sib is not None and sib.id != child.id:
                    used_by_siblings.add(sib.name)
        candidates = [n for n in ui_rng.sample(names, min(len(names), 12)) if n not in used_by_siblings]
        suggestions = [n for n in candidates if n != child.name][:8]
        relation = None
        player = world.player
        if player is not None:
            relation = _relation(world, player, child)
        out.append(
            {
                "child_id": child.id,
                "suggested": entry.get("suggested", child.name),
                "child_name": display_name(world, child),
                "gender": child.gender,
                "culture": culture,
                "culture_label": i18n.t(f"culture.{culture}"),
                "relation": relation or i18n.t("relation.descendant"),
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
                "culture_label": i18n.t(f"culture.{dyn.culture}"),
                "head": dyn.head,
                "head_name": display_name(world, head) if head else None,
                "renown": round(dyn.renown, 1),
                "members": len(dyn.members),
                "alive_members": len(alive_members),
                "legacies": dict(dyn.legacies),
            }
        )
    out.sort(key=lambda d: -d["renown"])
    return out


def _tutoring_entries(world: World) -> list[dict]:
    player = world.player
    out = []
    for entry in world.tutoring_queue:
        child = world.get(entry.get("child_id"))
        if child is None:
            continue
        focus = child.education_focus or "diplomacy"
        cands = sorted(
            [
                c
                for c in world.alive()
                if c.dynasty == child.dynasty and c.is_adult and c.id != child.id
            ],
            key=lambda g: g.attributes.get(focus, 0) + g.attributes.get("learning", 0) * 0.5,
            reverse=True,
        )[:6]
        guardian_candidates = [
            {
                "id": g.id,
                "name": display_name(world, g),
                "age": g.age,
                "skill": g.attributes.get(focus, 0),
                "learning": g.attributes.get("learning", 0),
                "suggested": i == 0,
            }
            for i, g in enumerate(cands)
        ]
        out.append(
            {
                "child_id": child.id,
                "name": display_name(world, child),
                "gender": child.gender,
                "age": child.age,
                "childhood_trait": (
                    {"id": child.childhood_trait, "name": T.childhood_name(child.childhood_trait)}
                    if child.childhood_trait else None
                ),
                "relation": _relation(world, player, child) if player else None,
                "suggested_focus": focus,
                "focus_options": [
                    {"key": k, "label": i18n.t(f"attr.{k}")} for k in T.education_routes()
                ],
                "guardian_candidates": guardian_candidates,
            }
        )
    return out


def _traitpick_entries(world: World) -> list[dict]:
    player = world.player
    out = []
    for entry in world.trait_queue:
        child = world.get(entry.get("child_id"))
        if child is None:
            continue
        taught, stray = genetics.trait_pick_options(
            world, child, random.Random(f"traits-{child.id}-{entry.get('age', child.age)}")
        )
        options = [
            {"id": taught, "name": T.trait_name(taught), "kind": "taught"},
            {"id": stray, "name": T.trait_name(stray), "kind": "stray"},
        ]
        guardian = world.get(child.guardian)
        out.append(
            {
                "child_id": child.id,
                "name": display_name(world, child),
                "gender": child.gender,
                "age": child.age,
                "relation": _relation(world, player, child) if player else None,
                "guardian_name": display_name(world, guardian) if guardian else None,
                "existing": [T.trait_name(t) for t in sorted(child.traits)],
                "options": options,
            }
        )
    return out


def betrothal_pools_payload(world: World) -> dict:
    player = world.player
    if player is None:
        return {"own": [], "other": []}
    own, other = marriage.betrothal_pools(world, player.id)
    return {
        "own": [enrich_character(world, c, player) for c in own],
        "other": [enrich_character(world, c, player) for c in other],
    }


def _legacies_payload(world: World) -> dict:
    player = world.player
    dyn = world.dynasties.get(player.dynasty) if player and player.dynasty is not None else None
    trees = []
    for t in legacy.TREES:
        lvl = legacy.level_of(dyn, t["id"]) if dyn else 0
        cost = legacy.legacy_cost(lvl) if lvl < legacy.MAX_LEVEL else None
        trees.append(
            {
                "id": t["id"],
                "label": i18n.t(f"legacy.tree.{t['id']}"),
                "desc": i18n.t(t["desc_key"]),
                "level": lvl,
                "max": legacy.MAX_LEVEL,
                "cost": cost,
                "affordable": bool(dyn and cost is not None and dyn.renown >= cost),
            }
        )
    return {
        "renown": round(dyn.renown) if dyn else 0,
        "dynasty": dyn.id if dyn else None,
        "trees": trees,
    }


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
            "label": i18n.t("date.label", year=date.year, month=date.month, xun=i18n.t(f"xun.{date.xun}")),
        },
        "player_id": world.player_id,
        "over": world.over,
        "over_reason": world.over_reason,
        "gender_law": world.gender_law,
        "gender_law_label": i18n.t(f"gender_law.{world.gender_law}"),
        "characters": [enrich_character(world, c, player) for c in world.characters.values()],
        "dynasties": _dynasties(world),
        "events": list(world.events),
        "naming_queue": _naming_entries(world),
        "tutoring_queue": _tutoring_entries(world),
        "trait_queue": _traitpick_entries(world),
        "legacies": _legacies_payload(world),
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
            "attrs": [{"key": k, "label": i18n.t(f"attr.{k}")} for k in B.ATTRS],
            "xun_names": [i18n.t(f"xun.{i}") for i in range(3)],
            "health_tiers": [
                {"floor": None if f == float("-inf") else f, "key": k, "label": i18n.t(f"health.tier.{k}")}
                for f, k in HEALTH_TIER_KEYS
            ],
            "consort_limit": B.CONSORT_LIMIT,
            "start_year": B.START_YEAR,
            "cultures": {c: i18n.t(f"culture.{c}") for c in ("czech", "polish", "hungarian", "german")},
            "gender_laws": {
                g: i18n.t(f"gender_law.{g}") for g in ("male_preference", "equal", "female_preference")
            },
        },
    }
