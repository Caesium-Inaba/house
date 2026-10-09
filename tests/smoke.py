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


def test_trait_mutex() -> None:
    """性情抉择：候选与获得的特质不得与自身互斥（矛盾性格不可共存，CK3 成对结构）。"""
    from house.core import genetics
    from house.core import traits as T

    for seed in range(20):
        world = build_default_world(100 + seed)
        player = world.player
        # 构造已有「暴怒」的适龄孩童
        teen = next((c for c in world.alive() if 9 <= c.age < 16), None)
        if teen is None:
            continue
        teen.traits = {"wroth"}
        for _ in range(200):
            taught, stray = genetics.trait_pick_options(world, teen)
            for cand in (taught, stray):
                own = T.PERSONALITY.get(cand, {}).get("opposites", [])
                assert cand not in teen.traits, f"{cand} 已有仍被推荐"
                assert not (set(own) & teen.traits), f"{cand} 与自身 {teen.traits} 互斥却出现"
            # 两候选之间也不应互斥
            assert stray not in T.PERSONALITY.get(taught, {}).get("opposites", []), (
                f"两候选互斥：{taught} ↔ {stray}"
            )
        # apply 层防御：直接注入互斥特质必须无效
        before = set(teen.traits)
        genetics.apply_trait_pick(world, teen, "calm")
        assert set(teen.traits) == before, "互斥特质被强行写入"
        # 非互斥特质可正常获得
        genetics.apply_trait_pick(world, teen, "brave")
        assert "brave" in teen.traits
        break
    print("[mutex] OK  性情抉择不产生互斥特质，apply 层防御生效")


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


def test_queue_timeout() -> None:
    """事件队列超时：逾期条目 sweep 自动落定，未到期的保留（事件不阻塞时间）。"""
    from house.core import queues

    world = build_default_world(6)
    victim = world.alive()[0]
    # 已到期的命名礼 → sweep 自动落定并移除
    entry = world.stamp_due({"child_id": victim.id, "suggested": victim.name})
    entry["due"] = [world.date.year, world.date.month]
    world.naming_queue.append(entry)
    queues.sweep(world)
    assert not world.naming_queue, "逾期命名礼未被自动落定"
    # 未到期的 → 保留
    entry2 = world.stamp_due({"child_id": victim.id, "suggested": "未到期者"})
    world.naming_queue.append(entry2)
    queues.sweep(world)
    assert any(x.get("child_id") == victim.id for x in world.naming_queue), "未到期条目被误清"
    print("[queue] OK  超时自动落定，未到期保留")


def main() -> None:
    test_core()
    test_save_load()
    test_marriage()
    test_trait_mutex()
    test_queue_timeout()
    asyncio.run(test_app())
    print("\n全部冒烟测试通过 ✓")


if __name__ == "__main__":
    main()
