"""游戏时间：旬 / 月 / 年。"""

from __future__ import annotations

from dataclasses import dataclass

from .. import balance as B


@dataclass
class Date:
    year: int = 1066
    month: int = 1
    xun: int = 0

    def label(self) -> str:
        return f"{self.year}年{self.month}月 {B.XUN_NAMES[self.xun]}"

    def advance(self) -> tuple[bool, bool]:
        """推进一旬。返回 (是否进入新月, 是否进入新年)。"""
        self.xun += 1
        rolled_month = rolled_year = False
        if self.xun >= B.XUN_PER_MONTH:
            self.xun = 0
            self.month += 1
            rolled_month = True
            if self.month > B.MONTHS_PER_YEAR:
                self.month = 1
                self.year += 1
                rolled_year = True
        return rolled_month, rolled_year

    def to_dict(self) -> dict:
        return {"year": self.year, "month": self.month, "xun": self.xun}

    @classmethod
    def from_dict(cls, data: dict) -> "Date":
        return cls(year=data["year"], month=data["month"], xun=data["xun"])
