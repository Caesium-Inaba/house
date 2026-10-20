"""游戏时间：现代公历（Gregorian）日 / 月 / 年，一日一回合。

闰年规则：能被 4 整除且不能被 100 整除，或能被 400 整除。
"""

from __future__ import annotations

from dataclasses import dataclass

START_YEAR = 1066
MONTHS_PER_YEAR = 12

_MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def month_days(year: int, month: int) -> int:
    if month == 2 and is_leap(year):
        return 29
    return _MONTH_DAYS[month - 1]


def days_in_year(year: int) -> int:
    return 366 if is_leap(year) else 365


@dataclass
class Date:
    year: int = START_YEAR
    month: int = 1
    day: int = 1

    def advance(self) -> tuple[bool, bool]:
        """推进一日。返回 (是否进入新月, 是否进入新年)。"""
        self.day += 1
        rolled_month = rolled_year = False
        if self.day > month_days(self.year, self.month):
            self.day = 1
            self.month += 1
            rolled_month = True
            if self.month > MONTHS_PER_YEAR:
                self.month = 1
                self.year += 1
                rolled_year = True
        return rolled_month, rolled_year

    def ordinal(self) -> int:
        """自 START_YEAR-01-01 起的绝对日序号（事件超时等按天比较用）。"""
        days = 0
        for y in range(START_YEAR, self.year):
            days += days_in_year(y)
        for m in range(1, self.month):
            days += month_days(self.year, m)
        return days + self.day - 1

    def label_zh(self) -> str:
        """TUI 用的中文日期标签（WebUI 走 i18n 的 date.label）。"""
        return f"{self.year}年{self.month}月{self.day}日"

    def to_dict(self) -> dict:
        return {"year": self.year, "month": self.month, "day": self.day}

    @classmethod
    def from_dict(cls, data: dict) -> "Date":
        return cls(year=data["year"], month=data["month"], day=data["day"])
