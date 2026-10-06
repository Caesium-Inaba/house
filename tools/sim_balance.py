"""数值校准模拟：无 UI 跑若干年，观察人口 / 资源 / 属性是否通胀或枯竭。

用法：uv run python tools/sim_balance.py [年数] [种子]
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from house import balance as B  # noqa: E402
from house.core import sim  # noqa: E402
from house.core.scenario import build_default_world  # noqa: E402

YEARS = int(sys.argv[1]) if len(sys.argv) > 1 else 300
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 12345


def mean(values):
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    world = build_default_world(SEED)
    home = world.dynasties[1].name
    print(f"种子 {SEED}，起始 {world.date.year}，家族 {home}")
    print(f"{'年份':>6} {'人口':>5} {'家族':>5} {'外交':>6} {'谋略':>6} {'勇武':>6} {'max外交':>7} {'威望':>7} {'家族威望':>8}")

    for _ in range(0, YEARS, 10):
        for _ in range(3 * 12 * 10):
            sim.tick_xun(world)
            if world.over:
                break
        alive = world.alive()
        if not alive:
            break
        family = [c for c in alive if c.dynasty and world.dynasties[c.dynasty].name == home]
        player = world.player
        prestige = player.prestige if player else 0.0
        renown = world.dynasties[1].renown
        print(
            f"{world.date.year:>6} {len(alive):>5} {len(family):>5} "
            f"{mean([c.attributes['diplomacy'] for c in alive]):>6.1f} "
            f"{mean([c.attributes['intrigue'] for c in alive]):>6.1f} "
            f"{mean([c.attributes['prowess'] for c in alive]):>6.1f} "
            f"{max((c.attributes['diplomacy'] for c in alive), default=0):>7} "
            f"{prestige:>7.0f} {renown:>8.0f}"
        )
        if world.over:
            print("游戏结束：", world.over_reason)
            break

    print(f"\n结束于 {world.date.label()}，在世 {len(world.alive())} 人。")
    print(f"硬上限 {B.WORLD_HARD_CAP} / 软上限 {B.WORLD_SOFT_CAP}")


if __name__ == "__main__":
    main()
