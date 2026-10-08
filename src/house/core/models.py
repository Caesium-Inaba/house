"""核心数据模型：角色、家族、世界。"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from .. import balance as B


@dataclass
class Character:
    id: int
    name: str
    gender: str  # "male" / "female"
    birth_year: int
    dynasty: Optional[int] = None
    father: Optional[int] = None
    mother: Optional[int] = None
    spouse: Optional[int] = None
    patrilineal: bool = True            # 婚姻是否父系（决定子女家族）
    children: list[int] = field(default_factory=list)
    death_year: Optional[int] = None
    death_reason: Optional[str] = None

    attributes: dict[str, int] = field(
        default_factory=lambda: {k: B.ATTR_BASE for k in B.ATTR_KEYS}
    )
    potential: dict[str, int] = field(
        default_factory=lambda: {k: B.ATTR_BASE for k in B.ATTR_KEYS}
    )
    genes: dict[str, int] = field(default_factory=dict)  # 先天特质 id -> 1 隐性 / 2 显性
    traits: set[str] = field(default_factory=set)
    education: Optional[str] = None
    health: float = 5.0

    # ── 教育与教养（CK3） ──
    childhood_trait: Optional[str] = None   # 6 岁显现的童年特质 id
    education_focus: Optional[str] = None   # 教育方向（6 岁定）
    education_score: int = 0                # 教育得分（年度判定累计）
    guardian: Optional[int] = None          # 监护人 id
    betrothed: Optional[int] = None         # 婚约对象 id

    money: float = 0.0
    prestige: float = 0.0
    piety: float = 0.0

    opinions: dict[int, int] = field(default_factory=dict)  # 对他人好感 -100..100
    pregnancy_months: Optional[int] = None
    pregnancy_father: Optional[int] = None
    children_born: int = 0

    # ── 便捷属性 ──
    @property
    def is_alive(self) -> bool:
        return self.death_year is None

    @property
    def is_adult(self) -> bool:
        return self.age >= B.CHILDHOOD_END

    def age_at(self, year: int) -> int:
        end = self.death_year if self.death_year is not None else year
        return end - self.birth_year

    # 运行时缓存，由 World.refresh_ages() 按当前年份更新
    _age_cache: int = field(default=0, repr=False)

    @property
    def age(self) -> int:
        return self._age_cache

    @property
    def is_pregnant(self) -> bool:
        return self.pregnancy_months is not None

    def attr(self, key: str) -> int:
        return self.attributes.get(key, 0)

    @property
    def health_tier(self) -> str:
        tier = B.HEALTH_TIERS[0][1]
        for lower, name in B.HEALTH_TIERS:
            if self.health >= lower:
                tier = name
        return tier

    # ── 序列化 ──
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "gender": self.gender,
            "birth_year": self.birth_year,
            "dynasty": self.dynasty,
            "father": self.father,
            "mother": self.mother,
            "spouse": self.spouse,
            "patrilineal": self.patrilineal,
            "children": list(self.children),
            "death_year": self.death_year,
            "death_reason": self.death_reason,
            "attributes": dict(self.attributes),
            "potential": dict(self.potential),
            "genes": {k: v for k, v in self.genes.items()},
            "traits": sorted(self.traits),
            "education": self.education,
            "childhood_trait": self.childhood_trait,
            "education_focus": self.education_focus,
            "education_score": self.education_score,
            "guardian": self.guardian,
            "betrothed": self.betrothed,
            "health": self.health,
            "money": self.money,
            "prestige": self.prestige,
            "piety": self.piety,
            "opinions": {str(k): v for k, v in self.opinions.items()},
            "pregnancy_months": self.pregnancy_months,
            "pregnancy_father": self.pregnancy_father,
            "children_born": self.children_born,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        ch = cls(
            id=data["id"],
            name=data["name"],
            gender=data["gender"],
            birth_year=data["birth_year"],
            dynasty=data.get("dynasty"),
            father=data.get("father"),
            mother=data.get("mother"),
            spouse=data.get("spouse"),
            patrilineal=data.get("patrilineal", True),
            children=list(data.get("children", [])),
            death_year=data.get("death_year"),
            death_reason=data.get("death_reason"),
            attributes=dict(data.get("attributes", {k: B.ATTR_BASE for k in B.ATTR_KEYS})),
            potential=dict(data.get("potential", {k: B.ATTR_BASE for k in B.ATTR_KEYS})),
            genes={k: int(v) for k, v in data.get("genes", {}).items()},
            traits=set(data.get("traits", [])),
            education=data.get("education"),
            childhood_trait=data.get("childhood_trait"),
            education_focus=data.get("education_focus"),
            education_score=data.get("education_score", 0),
            guardian=data.get("guardian"),
            betrothed=data.get("betrothed"),
            health=data.get("health", 5.0),
            money=data.get("money", 0.0),
            prestige=data.get("prestige", 0.0),
            piety=data.get("piety", 0.0),
            opinions={int(k): v for k, v in data.get("opinions", {}).items()},
            pregnancy_months=data.get("pregnancy_months"),
            pregnancy_father=data.get("pregnancy_father"),
            children_born=data.get("children_born", 0),
        )
        return ch


@dataclass
class Dynasty:
    id: int
    name: str
    culture: str = "czech"
    members: list[int] = field(default_factory=list)
    head: Optional[int] = None
    renown: float = 0.0
    legacies: dict[str, int] = field(default_factory=dict)  # 传承树 id -> 等级

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "culture": self.culture,
            "members": list(self.members),
            "head": self.head,
            "renown": self.renown,
            "legacies": dict(self.legacies),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Dynasty":
        return cls(
            id=data["id"],
            name=data["name"],
            culture=data.get("culture", "czech"),
            members=list(data.get("members", [])),
            head=data.get("head"),
            renown=data.get("renown", 0.0),
            legacies={str(k): int(v) for k, v in data.get("legacies", {}).items()},
        )


def new_rng(seed: Optional[int] = None) -> random.Random:
    return random.Random(seed)
