"""冒烟测试：核心逻辑 + 存读档 + TUI 启动与交互。

用法：uv run python tests/smoke.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from house import balance as B  # noqa: E402
from house.core import marriage, save, sim  # noqa: E402
from house.core.scenario import build_default_world  # noqa: E402


def test_core() -> None:
    world = build_default_world(1)
    assert world.player is not None
    start = (world.date.year, world.date.month, world.date.xun)
    sim.tick_xun(world)
    assert (world.date.year, world.date.month, world.date.xun) != start
    # 推进 40 年，家族不应绝嗣，人口不应爆炸
    sim.advance(world, 3 * 12 * 40)
    alive = world.alive()
    assert alive, "家族不应绝嗣"
    assert len(alive) <= B.WORLD_HARD_CAP + 40, f"人口失控：{len(alive)}"
    mx = max(c.attributes["diplomacy"] for c in alive)
    assert mx < B.ATTR_MAX, f"属性通胀：{mx}"
    print(f"[core] OK  年份 {world.date.year}  人口 {len(alive)}  max外交 {mx}")


def test_save_load() -> None:
    world = build_default_world(2)
    sim.advance(world, 3 * 12 * 5)
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "save.json")
        save.save_world(world, path)
        loaded = save.load_world(path)
    assert loaded.date.year == world.date.year
    assert loaded.player_id == world.player_id
    assert set(loaded.characters) == set(world.characters)
    original = world.get(world.player_id)
    copy = loaded.get(loaded.player_id)
    assert copy is not None and original is not None
    assert copy.name == original.name and copy.age == original.age
    print(f"[save] OK  读档后 {loaded.player.name if loaded.player else '?'}")


def test_marriage() -> None:
    world = build_default_world(3)
    player = world.player
    cands = marriage.candidates(world, player.id)
    # 玩家默认已婚，候选应为空或可被过滤
    assert all(c.id != player.id for c in cands)
    print(f"[marry] OK  候选 {len(cands)} 人")


async def test_app() -> None:
    from house.ui.app import HouseApp

    app = HouseApp(build_default_world(4))
    async with app.run_test() as pilot:
        await pilot.click("#tick1")
        await pilot.click("#family")
        await pilot.pause()
        await pilot.click("#back")
        await pilot.click("#marry")
        await pilot.pause()
        await pilot.click("#back")
        await pilot.click("#tick12")
        await pilot.pause()
    print("[tui] OK  启动、推进、家族树、婚配页均可交互")


def main() -> None:
    test_core()
    test_save_load()
    test_marriage()
    asyncio.run(test_app())
    print("\n全部冒烟测试通过 ✓")


if __name__ == "__main__":
    main()
