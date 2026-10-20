"""冒烟测试：核心逻辑 + 存读档 + TUI 启动与交互。

用法：uv run python tests/smoke.py
"""

from __future__ import annotations

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
    start = (world.date.year, world.date.month, world.date.day)
    sim.tick_day(world)
    assert (world.date.year, world.date.month, world.date.day) != start
    # 推进 40 年，家族不应绝嗣，人口不应爆炸
    sim.advance(world, 365 * 40)
    alive = world.alive()
    assert alive, "家族不应绝嗣"
    assert len(alive) <= B.WORLD_HARD_CAP + 40, f"人口失控：{len(alive)}"
    mx = max(c.attributes["diplomacy"] for c in alive)
    assert mx < B.ATTR_MAX, f"属性通胀：{mx}"
    print(f"[core] OK  年份 {world.date.year}  人口 {len(alive)}  max外交 {mx}")


def test_save_load() -> None:
    world = build_default_world(2)
    sim.advance(world, 365 * 5)
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




def test_queue_timeout() -> None:
    """事件队列超时：逾期条目 sweep 自动落定，未到期的保留（事件不阻塞时间）。"""
    from house.core import queues

    world = build_default_world(6)
    victim = world.alive()[0]
    # 已到期的命名礼 → sweep 自动落定并移除
    entry = world.stamp_due({"child_id": victim.id, "suggested": victim.name})
    entry["due"] = world.date.ordinal()  # 立刻到期
    world.naming_queue.append(entry)
    queues.sweep(world)
    assert not world.naming_queue, "逾期命名礼未被自动落定"
    # 未到期的 → 保留
    entry2 = world.stamp_due({"child_id": victim.id, "suggested": "未到期者"})
    world.naming_queue.append(entry2)
    queues.sweep(world)
    assert any(x.get("child_id") == victim.id for x in world.naming_queue), "未到期条目被误清"
    print("[queue] OK  超时自动落定，未到期保留")


def test_rename_events() -> None:
    """统一改名入口：只改「此人是 actor」的历史事件，他人独立事件不受影响。"""
    world = build_default_world(9)
    victim = world.alive()[0]
    other = next(c for c in world.alive() if c.id != victim.id)
    old = victim.name

    world.add_event("marriage", "event.marriage", {"a": old, "b": old}, [victim.id, other.id])
    mixed_id = len(world.events) - 1
    world.add_event("marriage", "event.marriage", {"a": other.name}, [other.id])
    other_only_id = len(world.events) - 1

    world.rename_character(victim.id, "试验新名")
    mixed = world.events[mixed_id]
    # 同事件内同名字符串不可区分，两值一并替换（接受为仅视觉影响）
    assert mixed["params"]["a"] == "试验新名" and mixed["params"]["b"] == "试验新名"
    assert "试验新名" in mixed["text"]
    other_only = world.events[other_only_id]
    assert other_only["params"]["a"] == other.name, "无关事件被误改"
    assert other.name == old or "试验新名" not in other_only.get("text", "")
    assert victim.name == "试验新名"
    # 不存在的 id / 空名 / 同名 → 不崩溃不变更
    world.rename_character(99999, "x")
    world.rename_character(victim.id, "试验新名")
    assert victim.name == "试验新名"
    print(f"[rename] OK  仅此人 actor 事件被同步（{old} → 试验新名）")


def test_mods_overlay() -> None:
    """模组覆盖：数据按键深合并、语言覆盖、关闭后回滚回原版。"""
    import json
    import os
    import tempfile
    from pathlib import Path

    from house import i18n
    from house.core import mods as M
    from house.core import traits as T

    vanilla_loc = i18n.t("health.tier.good")
    vanilla_traits = dict(T.TRAITS)
    assert "intellect_p1" in T.TRAITS  # vanilla 基线

    cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        trial = Path("mods/trial")
        (trial / "data").mkdir(parents=True)
        (trial / "localization").mkdir()
        (trial / "mod.json").write_text(
            json.dumps({"name": "试验模组", "version": "1.0", "tags": ["test"]}, ensure_ascii=False),
            encoding="utf-8",
        )
        (trial / "data" / "traits.json").write_text(
            json.dumps({"personality": {"brave": {"money_pct": 0.9}}}, ensure_ascii=False),
            encoding="utf-8",
        )
        (trial / "data" / "names.json").write_text(
            json.dumps({"cultures": {"german": {"male": ["试验男名"]}}}, ensure_ascii=False),
            encoding="utf-8",
        )
        (trial / "localization" / "zh.json").write_text(
            json.dumps({"health.tier.good": "试验·尚可"}, ensure_ascii=False),
            encoding="utf-8",
        )
        M.save_config(["trial"])
        T.reload_data()

        raw = T.load_json("traits.json")
        assert raw["personality"]["brave"]["money_pct"] == 0.9, "深合并未生效"
        assert "试验男名" in T.load_json("names.json")["cultures"]["german"]["male"]
        assert T.TRAITS.get("brave", {}).get("money_pct") == 0.9, "TRAITS 未重载"
        assert i18n.t("health.tier.good") == "试验·尚可", "语言覆盖未生效"
        # launcher.json 已落盘
        assert M.load_config()["enabled"] == ["trial"]

        # 关闭 → 回滚原版
        M.save_config([])
        T.reload_data()
        assert T.load_json("traits.json")["personality"]["brave"].get("money_pct") is None
        assert i18n.t("health.tier.good") == vanilla_loc
        assert set(T.TRAITS) == set(vanilla_traits)
        os.chdir(cwd)  # 先离开临时目录才能清理它（Windows 不可 rmtree 当前目录）
    # 回到真实工作目录后恢复原状（无 mods 配置）
    T.reload_data()
    print("[mods] OK  覆盖生效/回滚正确")


def main() -> None:
    test_core()
    test_save_load()
    test_marriage()
    test_trait_mutex()
    test_queue_timeout()
    test_rename_events()
    test_mods_overlay()
    print("\n全部冒烟测试通过 ✓")


if __name__ == "__main__":
    main()
