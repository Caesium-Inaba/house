"""继承桥接（M2 简化版）：玩家死亡后选择继承人。

M3 会由完整头衔 + 继承法替换本模块的选人逻辑。
"""

from __future__ import annotations

from typing import Optional

from .models import Character
from .world import World


def _pick(cands: list[Character], law: str) -> Character:
    if law == "male_preference":
        cands.sort(key=lambda c: (0 if c.gender == "male" else 1, c.birth_year))
    elif law == "female_preference":
        cands.sort(key=lambda c: (0 if c.gender == "female" else 1, c.birth_year))
    else:
        cands.sort(key=lambda c: c.birth_year)
    return cands[0]


def find_heir(world: World, deceased: Character) -> Optional[Character]:
    """继承人必须与逝者同家族（保证玩家在同一家族内延续）。

    顺序：同家族子女 → 同家族兄弟姐妹 → 同家族旁系。都没有才算绝嗣。
    """
    dyn = deceased.dynasty

    def same_house(c: Character) -> bool:
        return dyn is None or c.dynasty == dyn

    children = [world.get(cid) for cid in deceased.children]
    children = [c for c in children if c is not None and c.is_alive and same_house(c)]
    if children:
        return _pick(children, world.gender_law)

    siblings: list[Character] = []
    for c in world.alive():
        if c.id == deceased.id or not same_house(c):
            continue
        same_father = deceased.father is not None and c.father == deceased.father
        same_mother = deceased.mother is not None and c.mother == deceased.mother
        if same_father or same_mother:
            siblings.append(c)
    if siblings:
        return _pick(siblings, world.gender_law)

    if dyn is not None:
        kin = [c for c in world.alive() if c.dynasty == dyn and c.id != deceased.id]
        if kin:
            return _pick(kin, world.gender_law)
    return None


def handle_player_death(world: World) -> None:
    player = world.player
    if player is None or player.is_alive or world.over:
        return
    heir = find_heir(world, player)
    if heir is None:
        world.over = True
        world.over_reason = "家族绝嗣，无人继承"
        world.add_log("☠ 家族绝嗣，故事就此终结。")
        world.add_event("extinction", "家族绝嗣，故事就此终结。")
        return
    world.player_id = heir.id
    if heir.dynasty is not None and heir.dynasty in world.dynasties:
        world.dynasties[heir.dynasty].head = heir.id
    world.add_log(f"👑 {heir.name} 继承家主之位（{heir.age}岁）。")
    world.add_event("succession", f"{heir.name} 继承家主之位（{heir.age}岁）。", [heir.id, player.id])
