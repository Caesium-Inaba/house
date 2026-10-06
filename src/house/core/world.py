"""世界状态：角色 / 家族 / 时间的容器与基础操作。"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from .models import Character, Dynasty
from .time import Date


@dataclass
class World:
    date: Date = field(default_factory=Date)
    characters: dict[int, Character] = field(default_factory=dict)
    dynasties: dict[int, Dynasty] = field(default_factory=dict)
    player_id: Optional[int] = None
    next_char_id: int = 1
    next_dynasty_id: int = 1
    rng: random.Random = field(default_factory=random.Random)
    log: list[str] = field(default_factory=list)
    over: bool = False
    over_reason: str = ""
    gender_law: str = "male_preference"  # male_preference / equal / female_preference

    # ── 基础操作 ──
    def new_char_id(self) -> int:
        cid = self.next_char_id
        self.next_char_id += 1
        return cid

    def add_dynasty(self, name: str, culture: str = "czech") -> Dynasty:
        did = self.next_dynasty_id
        self.next_dynasty_id += 1
        dyn = Dynasty(id=did, name=name, culture=culture)
        self.dynasties[did] = dyn
        return dyn

    def add_character(self, char: Character) -> Character:
        self.characters[char.id] = char
        if char.dynasty is not None and char.dynasty in self.dynasties:
            member_ids = self.dynasties[char.dynasty].members
            if char.id not in member_ids:
                member_ids.append(char.id)
        return char

    def get(self, cid: Optional[int]) -> Optional[Character]:
        if cid is None:
            return None
        return self.characters.get(cid)

    @property
    def player(self) -> Optional[Character]:
        return self.get(self.player_id)

    def refresh_ages(self) -> None:
        for ch in self.characters.values():
            ch._age_cache = ch.age_at(self.date.year)

    def alive(self) -> list[Character]:
        return [c for c in self.characters.values() if c.is_alive]

    def add_log(self, msg: str) -> None:
        self.log.append(msg)
        if len(self.log) > 400:
            del self.log[: len(self.log) - 400]

    def name_of(self, cid: Optional[int]) -> str:
        ch = self.get(cid)
        return ch.name if ch else "（无）"

    def dynasty_name_of(self, cid: Optional[int]) -> str:
        ch = self.get(cid)
        if not ch or ch.dynasty is None:
            return ""
        dyn = self.dynasties.get(ch.dynasty)
        return dyn.name if dyn else ""

    def is_ruler(self, char: Character) -> bool:
        """M2 占位：玩家本人视为统治者，其余为非统治者（生育力 -15% 修正）。"""
        return char.id == self.player_id
