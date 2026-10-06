"""回合推进与结算编排。"""

from __future__ import annotations

from .. import balance as B
from . import fertility, genetics, health, inheritance, marriage, opinion
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

    world.refresh_ages()
    inheritance.handle_player_death(world)


def advance(world: World, xuns: int) -> None:
    for _ in range(xuns):
        tick_xun(world)
        if world.over:
            break


def monthly_settlement(world: World) -> None:
    fertility.monthly_settlement(world)
    marriage.ai_marriages(world)
    opinion.monthly_decay(world)


def yearly_settlement(world: World) -> None:
    health.yearly_health(world)
    world.refresh_ages()
    genetics.grow_children(world)
    _yearly_resources(world)


def _yearly_resources(world: World) -> None:
    for char in world.alive():
        if char.dynasty is not None and char.dynasty in world.dynasties:
            world.dynasties[char.dynasty].renown += B.RENOWN_YEARLY_BASE * 0.1
    player = world.player
    if player is not None and player.is_alive:
        player.prestige += B.PRESTIGE_YEARLY_BASE + player.attr("diplomacy") * 0.2
        player.piety += B.PIETY_YEARLY_BASE
        player.money += B.MONEY_YEARLY_BASE + player.attr("stewardship") * 0.3
