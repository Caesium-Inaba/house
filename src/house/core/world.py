"""世界状态：角色 / 家族 / 时间的容器与基础操作。"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .models import Character, Dynasty
from .time import Date

EVENT_CAP = 400


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
    # 结构化事件流（WebUI 消费）：{year, month, day, type, text, actors}
    events: list[dict] = field(default_factory=list)
    naming_queue: list[dict] = field(default_factory=list)
    tutoring_queue: list[dict] = field(default_factory=list)  # 待定教养的玩家血亲儿童
    trait_queue: list[dict] = field(default_factory=list)  # 待「性情抉择」的玩家血亲儿童（9/12/15 岁）
    betrothals: list[dict] = field(default_factory=list)  # [{a, b, patrilineal}]
    head_history: list[int] = field(default_factory=list)  # 历代家主继位顺序（世数计数依据）
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

    def stamp_due(self, entry: dict, lag: int | None = None) -> dict:
        """事件入队时间戳：due = 当前日序号 + lag 天（默认 60 天，即两个月）。

        事件不阻塞时间流动（CK3 式），逾期未处理由 core/queues.sweep 自动落定。
        due 存绝对日序号（Date.ordinal），跨月与闰年无缝比较。
        """
        from .. import balance as B

        entry["due"] = self.date.ordinal() + (lag if lag is not None else B.EVENT_DUE_DAYS)
        return entry

    @property
    def player(self) -> Optional[Character]:
        return self.get(self.player_id)

    def refresh_ages(self) -> None:
        for ch in self.characters.values():
            ch._age_cache = ch.age_at(self.date.year, self.date.month, self.date.day)

    def alive(self) -> list[Character]:
        return [c for c in self.characters.values() if c.is_alive]

    def add_log(self, msg: str) -> None:
        self.log.append(msg)
        if len(self.log) > 400:
            del self.log[: len(self.log) - 400]

    def add_event(self, etype: str, key: str, params: dict | None = None, actors=()) -> None:
        """结构化事件（与 add_log 成对出现）。

        存 key + params（可重渲染多语言）与 text（发出时的中文快照，供旧展示/存档）。
        """
        from ..i18n import t as _t

        p = dict(params or {})
        self.events.append(
            {
                "year": self.date.year,
                "month": self.date.month,
                "day": self.date.day,
                "type": etype,
                "key": key,
                "params": p,
                "text": _t(key, **p),
                "actors": list(actors),
            }
        )
        if len(self.events) > EVENT_CAP:
            del self.events[: len(self.events) - EVENT_CAP]

    def name_of(self, cid: Optional[int]) -> str:
        ch = self.get(cid)
        return ch.name if ch else "（无）"

    def rename_character(self, cid: int, new_name: str) -> None:
        """统一改名入口：更新人物名，并同步历史事件与待命名队列。

        - 历史事件只替换「此人是 actor」的条目（text 与 params 的字符串值），
          同名他人的事件不受影响；同一事件内另一 actor 撞同一个名时字符串
          层面不可区分，接受为仅视觉影响（同名者实际将继续共用该写法）。
        - world.log（TUI 遗留日志）是纯字符串、无 actor 定向，不做替换；
          玩家面向的日志是编年史（events 流），已覆盖。
        - 待命名队列里该人的 recommended 名同步更新，防止命名礼超时落定
          用旧推荐名把手动改名覆盖回去。
        """
        char = self.get(cid)
        if char is None or not new_name:
            return
        old = char.name
        if old == new_name:
            return
        char.name = new_name
        for e in self.events:
            if cid not in e.get("actors", []):
                continue
            params = e.get("params")
            if isinstance(params, dict):
                for k, v in params.items():
                    if isinstance(v, str) and old in v:
                        params[k] = v.replace(old, new_name)
                    elif isinstance(v, list):
                        # 名字列表（如 birth 的 children）逐项替换
                        params[k] = [
                            item.replace(old, new_name) if isinstance(item, str) else item
                            for item in v
                        ]
            text = e.get("text")
            if isinstance(text, str) and old in text:
                e["text"] = text.replace(old, new_name)
        for entry in self.naming_queue:
            if entry.get("child_id") == cid and entry.get("suggested") == old:
                entry["suggested"] = new_name

    def dynasty_name_of(self, cid: Optional[int]) -> str:
        ch = self.get(cid)
        if not ch or ch.dynasty is None:
            return ""
        dyn = self.dynasties.get(ch.dynasty)
        return dyn.name if dyn else ""

    def is_ruler(self, char: Character) -> bool:
        """M2 占位：玩家本人视为统治者，其余为非统治者（生育力 -15% 修正）。"""
        return char.id == self.player_id

    def is_descendant(self, cid: int, ancestor_id: Optional[int]) -> bool:
        """cid 是否为 ancestor 的血亲后代（沿父母上溯，含外嫁女儿所生）。"""
        if ancestor_id is None:
            return False
        seen: set[int] = set()
        stack = [cid]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            if x == ancestor_id:
                return True
            ch = self.characters.get(x)
            if ch is None:
                continue
            if ch.father is not None:
                stack.append(ch.father)
            if ch.mother is not None:
                stack.append(ch.mother)
        return False
