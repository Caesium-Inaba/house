"""回合推进与结算编排（一日一回合，公历）。"""

from __future__ import annotations

from .. import balance as B
from . import fertility, genetics, health, inheritance, legacy, marriage, opinion, queues
from . import traits as T
from .world import World


def tick_day(world: World) -> None:
    """推进一日：生日结算逐人触发；每月 1 日跑月度结算；每年 1 月 1 日跑年度资源。"""
    if world.over:
        return
    rolled_month, rolled_year = world.date.advance()
    world.refresh_ages()

    if rolled_month:
        monthly_settlement(world)
    if rolled_year:
        _yearly_resources(world)

    fertility.daily_settlement(world)
    birthday_settlement(world)

    # 事件不阻塞时间（CK3 式）：待办逾期 60 天未处理则自动落定
    queues.sweep(world)

    inheritance.handle_player_death(world)


def advance(world: World, days: int, stop_on_naming: bool = False) -> None:
    """推进 days 日。

    备份（旧行为）：stop_on_naming=True 时遇到待命名队列即停——事件阻塞时间流动。
    该机制已保留；事件窗口化后默认走非阻塞（False）。
    """
    for _ in range(days):
        tick_day(world)
        if world.over:
            break
        if stop_on_naming and world.naming_queue:
            break


def monthly_settlement(world: World) -> None:
    """每月 1 日：受孕 roll、圆婚、AI 婚配、意见衰减。"""
    fertility.monthly_settlement(world)
    marriage.fulfill_betrothals(world)
    marriage.ai_marriages(world)
    opinion.monthly_decay(world)


def birthday_settlement(world: World) -> None:
    """生日当天：该角色的年度个人结算（健康衰减/死亡判定/成长/教育）。"""
    d = world.date
    for char in world.alive():
        if char.birth_month != d.month or char.birth_day != d.day:
            continue
        health.annual_person(world, char)
        if not char.is_alive:
            continue
        genetics.annual_growth(world, char)


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
