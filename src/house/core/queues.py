"""事件队列的超时自动落定（CK3 式：事件不阻塞时间，超时未操作则自动落定）。

设计要点：
- 每个玩家的待人事件（命名礼/教养礼/性情抉择）入队时打 due 时间戳（2 个月后）；
- 每旬 sweep 检查到期事件，按「推荐选项」落定；没有推荐则随机兜底；
- 旧的「事件弹出即停止推进」机制（sim.advance 的 stop_on_naming，现已默认关闭）
  仍完整保留在 sim.py / server.py 中，注释处可一键恢复阻塞式行为，供后续复用。
"""

from __future__ import annotations

import random

from . import genetics
from . import traits as T
from .. import i18n
from .world import World

DUE_LAG = 2  # 入队后 2 个月内未处理则自动落定（月）


def _overdue(entry: dict, y: int, m: int) -> bool:
    due = entry.get("due")
    if not due:
        return False  # 旧档/未打戳的条目不超时（保持原语义）
    return (y, m) >= (tuple(due))


def sweep(world: World) -> None:
    """每旬检查过期事件并自动落定。"""
    y, m = world.date.year, world.date.month

    # ── 命名礼：落定入队时的推荐名（缺省沿用出生名） ──
    for entry in list(world.naming_queue):
        if not _overdue(entry, y, m):
            continue
        child = world.get(entry.get("child_id", -1))
        if child is None:
            world.naming_queue.remove(entry)
            continue
        name = str(entry.get("suggested") or child.name)
        genetics.resolve_naming(world, child, name)
        world.naming_queue.remove(entry)

    # ── 教养礼：童年特质推定方向；监护人优先推荐位，缺则同族最佳、无则随机成人 ──
    for entry in list(world.tutoring_queue):
        if not _overdue(entry, y, m):
            continue
        child = world.get(entry.get("child_id", -1))
        if child is None:
            world.tutoring_queue.remove(entry)
            continue
        _fallback_tutor(world, child)
        world.tutoring_queue.remove(entry)

    # ── 性情抉择：优先「师长言传」，缺则随机一个不冲突的特质 ──
    for entry in list(world.trait_queue):
        if not _overdue(entry, y, m):
            continue
        child = world.get(entry.get("child_id", -1))
        if child is None:
            world.trait_queue.remove(entry)
            continue
        _fallback_trait(world, child)
        world.trait_queue.remove(entry)


def _fallback_tutor(world: World, child) -> None:
    focus = T.childhood_focus(child.childhood_trait) if child.childhood_trait else None
    genetics.auto_tutor(world, child)  # 设定 focus + 同族最佳监护人
    if focus:
        child.education_focus = focus
    guardian = world.get(child.guardian)
    genetics.add_tutoring_event(world, child, child.education_focus, guardian)


def _fallback_trait(world: World, child) -> None:
    taught, stray = genetics.trait_pick_options(world, child)
    pick = taught or stray
    if not pick:
        pool = list(T.PERSONALITY_IDS)
        pick = world.rng.choice(pool) if pool else ""
    if pick:
        genetics.apply_trait_pick(world, child, pick)
