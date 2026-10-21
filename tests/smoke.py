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
    world.player.stress = 42
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
    assert copy.stress == 42, "压力未随存档往返"
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




def test_stress() -> None:
    """压力：分档、崩溃入队与选择、5 年 CD、400 强制崩溃、AI 自动、血亲死亡、死亡通知。"""
    from house.core import decisions, health, inheritance, stress
    from house.core import traits as T

    world = build_default_world(11)
    player = world.player

    # 降压决议 + CD
    ok, key = decisions.apply(world, player, "meditate")
    assert ok, key
    assert player.decisions["meditate"] > world.date.ordinal()
    ok2, key2 = decisions.apply(world, player, "meditate")
    assert not ok2 and key2 == "api.decision_cd", (ok2, key2)

    # 跨 100 触发崩溃入队（玩家本人）
    stress.add_stress(world, player.id, 100)
    assert player.stress >= 100
    entry = next((e for e in world.stress_queue if e["char_id"] == player.id), None)
    assert entry is not None, "跨档未触发精神崩溃"
    option = entry["options"][0]
    assert stress.resolve_pending(world, player.id, option)
    assert option in player.traits
    assert player.stress < 100, "崩溃后未减压"
    assert not any(e["char_id"] == player.id for e in world.stress_queue)

    # 5 年 CD：再加压跨 200 不应立刻再崩
    stress.add_stress(world, player.id, 180)
    assert player.stress >= 200
    assert not any(e["char_id"] == player.id for e in world.stress_queue), "崩溃 CD 未生效"

    # 400 强制崩溃并清 100
    player.last_break_ordinal = None
    player.stress = 390
    stress.add_stress(world, player.id, 30)
    assert player.stress <= 320, player.stress
    assert any(e["char_id"] == player.id for e in world.stress_queue)

    # AI 自动崩溃：不入队但拿到应对特质
    ai = next(c for c in world.alive() if c.id != player.id and c.age >= 16)
    before_traits = set(ai.traits)
    stress.add_stress(world, ai.id, 120)
    assert not any(e["char_id"] == ai.id for e in world.stress_queue), "AI 崩溃不应入队"
    assert set(ai.traits) != before_traits, "AI 崩溃未自动获得特质"
    assert len([t for t in ai.traits if t in T.COPING_IDS]) <= 2

    # 血亲死亡 → 家长压力上升
    world2 = build_default_world(12)
    father = world2.player
    child = next(c for c in world2.alive() if c.father == father.id)
    before = father.stress
    health.kill(world2, child, "disease")
    assert father.stress > before, "血亲死亡未产生压力"

    # 玩家死亡通知
    world3 = build_default_world(13)
    health.kill(world3, world3.player, "disease")
    inheritance.handle_player_death(world3)
    assert world3.death_notice and world3.death_notice["heir_name"], world3.death_notice
    print("[stress] OK  分档/崩溃/CD/400/AI/悲痛/死亡通知")


def main() -> None:
    test_core()
    test_save_load()
    test_marriage()
    test_trait_mutex()
    test_queue_timeout()
    test_rename_events()
    test_mods_overlay()
    test_stress()
    print("\n全部冒烟测试通过 ✓")


if __name__ == "__main__":
    main()
