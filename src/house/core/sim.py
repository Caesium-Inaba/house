"""回合推进与结算编排。"""

from __future__ import annotations

from .. import balance as B
from . import fertility, genetics, health, inheritance, legacy, marriage, opinion, queues
from . import traits as T
from .world import World


def tick_xun(world: World) -> None:
    """推进一旬，并在月末 / 年末触发结算。"""
    if world.over:
        return
    world.refresh_ages()
    rolled_month, rolled_year = world.date.advance()
    world.refresh_ages()

    if rolled_month:
        monthly_settlement(world)
    if rolled_year:
        yearly_settlement(world)

    # 事件不阻塞时间（CK3 式）：待办逾期 2 个月未处理则自动落定
    queues.sweep(world)

    world.refresh_ages()
    inheritance.handle_player_death(world)


def advance(world: World, xuns: int, stop_on_naming: bool = False) -> None:
    """推进 xuns 旬。

    备份（旧行为）：stop_on_naming=True 时遇到待命名队列即停——事件阻塞时间流动。
    该机制已保留；事件窗口化上线后默认走非阻塞（False），如需恢复阻塞式推进，
    把 server.py /api/tick 的 stop_on_naming 改回 True 即可。
    """
    for _ in range(xuns):
        tick_xun(world)
        if world.over:
            break
        if stop_on_naming and world.naming_queue:
            break


def monthly_settlement(world: World) -> None:
    fertility.monthly_settlement(world)
    marriage.fulfill_betrothals(world)
    marriage.ai_marriages(world)
    opinion.monthly_decay(world)


def yearly_settlement(world: World) -> None:
    health.yearly_health(world)
    world.refresh_ages()
    genetics.grow_children(world)
    _yearly_resources(world)


def _yearly_resources(world: World) -> None:
    for char in world.alive():
        fm = legacy.family_modifiers(world, char.dynasty)
        im = T.income_mods(char.traits)
        if char.dynasty is not None and char.dynasty in world.dynasties:
            world.dynasties[char.dynasty].renown += B.RENOWN_YEARLY_BASE * 0.1
        player = world.player
        if char.id == (player.id if player else -1) and player is not None and player.is_alive:
            prestige = B.PRESTIGE_YEARLY_BASE + player.attr("diplomacy") * 0.2
            prestige += im["prestige_flat_yearly"]
            prestige *= (1 + im["prestige_pct"]) * (1 + fm.get("prestige_mult", 0.0))
            player.prestige += prestige
            piety = B.PIETY_YEARLY_BASE
            piety += im["piety_flat_yearly"]
            piety *= (1 + im["piety_pct"])
            player.piety += max(0.0, piety)
            money = B.MONEY_YEARLY_BASE + player.attr("stewardship") * 0.3
            money *= (1 + im["money_pct"]) * (1 + fm.get("money_mult", 0.0))
            player.money += max(0.0, money)
