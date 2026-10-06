"""Textual 界面：主界面 + 家族树 + 婚配。手机竖屏优先。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from .. import balance as B
from ..core import marriage, save, sim
from ..core.models import Character
from ..core.scenario import build_default_world

SAVE_PATH = Path("save.json")


def _fmt_attrs(char: Character) -> str:
    parts = [f"{B.ATTRS[k]}{char.attributes.get(k, 0)}" for k in B.ATTR_KEYS]
    return "  ".join(parts)


def _char_line(world, char: Character, indent: int = 0) -> str:
    pad = "  " * indent
    mark = "" if char.is_alive else " ✝"
    gender = "♂" if char.gender == "male" else "♀"
    return f"{pad}{gender} {char.name}{mark}（{char.age}岁）"


def render_family_tree(world, root: Optional[Character]) -> str:
    lines: list[str] = []
    if root is None:
        return "（无家主）"

    def walk(char: Character, depth: int) -> None:
        lines.append(_char_line(world, char, depth))
        for cid in char.children:
            child = world.get(cid)
            if child is not None and child.is_alive:
                walk(child, depth + 1)

    lines.append("[b]家主一脉[/b]")
    walk(root, 0)

    # 同族其他在世成员
    if root.dynasty is not None:
        tree_ids = set()
        stack = [root]
        while stack:
            c = stack.pop()
            tree_ids.add(c.id)
            for cid in c.children:
                ch = world.get(cid)
                if ch is not None and ch.is_alive:
                    stack.append(ch)
        others = [
            c
            for c in world.alive()
            if c.dynasty == root.dynasty and c.id not in tree_ids
        ]
        if others:
            lines.append("")
            lines.append("[b]同族旁支[/b]")
            for c in others[:40]:
                lines.append(_char_line(world, c))
    return "\n".join(lines)


class MainScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Container(id="body"):
            yield Static(id="status")
            with VerticalScroll(id="log_scroll"):
                yield Static(id="log")
            with Container(id="buttons"):
                yield Button("推进一旬", id="tick1", variant="primary")
                yield Button("推进一年", id="tick12")
                yield Button("家族树", id="family")
                yield Button("婚配", id="marry")
                yield Button("存档", id="save")
                yield Button("读档", id="load")
                yield Button("退出", id="quit", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_view()

    def refresh_view(self) -> None:
        world = self.app.world
        player = world.player
        if player is None:
            self.query_one("#status", Static).update("（无家主）")
        else:
            dyn = world.dynasty_name_of(player.id)
            spouse = world.name_of(player.spouse) if player.spouse else "未婚"
            preg = ""
            if player.is_pregnant:
                preg = f"  怀孕中（余{player.pregnancy_months}月）"
            edu = ""
            from ..core import traits as T

            if player.education:
                edu = f"  {T.education_name(player.education)}"
            status = (
                f"[b]{player.name}[/b]  {dyn}家族  {'♂' if player.gender=='male' else '♀'}  {player.age}岁{edu}\n"
                f"健康：{player.health_tier}（{player.health:.2f}）   配偶：{spouse}{preg}\n"
                f"{_fmt_attrs(player)}\n"
                f"金钱 {player.money:.0f}   威望 {player.prestige:.0f}   虔诚 {player.piety:.0f}   "
                f"子女 {len(player.children)}   在世 {len(world.alive())}"
            )
            self.query_one("#status", Static).update(status)

        log = world.log[-40:] if world.log else ["（尚无大事发生）"]
        self.query_one("#log", Static).update("\n".join(reversed(log)))
        if world.over:
            self.query_one("#status", Static).update(
                f"[b red]{world.over_reason}[/b red]\n可读档继续，或退出。"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "tick1":
            sim.tick_xun(self.app.world)
        elif bid == "tick12":
            sim.advance(self.app.world, B.XUN_PER_MONTH * B.MONTHS_PER_YEAR)
        elif bid == "family":
            self.app.push_screen(FamilyTreeScreen())
            return
        elif bid == "marry":
            self.app.push_screen(MarriageScreen())
            return
        elif bid == "save":
            save.save_world(self.app.world, SAVE_PATH)
            self.app.notify(f"已存档到 {SAVE_PATH}")
        elif bid == "load":
            if SAVE_PATH.exists():
                self.app.world = save.load_world(SAVE_PATH)
                self.app.notify("已读档")
            else:
                self.app.notify("没有找到存档", severity="warning")
        elif bid == "quit":
            self.app.exit()
            return
        self.refresh_view()


class FamilyTreeScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with VerticalScroll():
            yield Static(render_family_tree(self.app.world, self.app.world.player))
        yield Button("返回", id="back", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()


class MarriageScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        player = self.app.world.player
        with VerticalScroll():
            yield Static("[b]选择一位婚配对象[/b]（仅显示可婚配者）")
            if player is None:
                yield Static("（无家主）")
            else:
                cands = marriage.candidates(self.app.world, player.id)
                if not cands:
                    yield Static("（暂无可婚配对象；可推进时间等新的人成年）")
                for c in cands:
                    dyn = self.app.world.dynasty_name_of(c.id)
                    label = (
                        f"{'♂' if c.gender=='male' else '♀'} {c.name} · {dyn} · {c.age}岁 · "
                        f"{_fmt_attrs(c)}"
                    )
                    yield Button(label, id=f"m_{c.id}")
        yield Button("返回", id="back", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "back":
            self.app.pop_screen()
            return
        if bid.startswith("m_"):
            target_id = int(bid[2:])
            player = self.app.world.player
            if player is None:
                return
            ok = marriage.arrange_marriage(self.app.world, player.id, target_id)
            if ok:
                self.app.notify("婚姻达成")
                self.app.pop_screen()
                self.app.refresh_current()
            else:
                self.app.notify("无法成婚", severity="warning")


class HouseApp(App):
    CSS = """
    Screen { layout: vertical; }
    #body { height: 1fr; }
    #status {
        border: round $primary;
        padding: 0 1;
        height: auto;
    }
    #log_scroll { height: 1fr; border: round $secondary; padding: 0 1; }
    #log { height: auto; }
    #buttons {
        layout: grid;
        grid-size: 2;
        grid-gutter: 0 1;
        height: auto;
        margin-top: 1;
    }
    #buttons Button { width: 100%; margin-bottom: 0; }
    Button { min-width: 8; }
    """

    def __init__(self, world=None):
        super().__init__()
        self.world = world or build_default_world()

    def on_mount(self) -> None:
        self.push_screen(MainScreen())

    def refresh_current(self) -> None:
        screen = self.screen
        if isinstance(screen, MainScreen):
            screen.refresh_view()


def run() -> None:
    HouseApp().run()
