"""横屏 TUI：左人物 / 中事件 / 右操作，家族树满屏可点选。竖屏版见 app.py。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Static, Tree

from .. import balance as B
from ..core import marriage, save, sim
from ..core import traits as T
from ..core.models import Character
from ..core.scenario import build_default_world

SAVE_PATH = Path("save.json")


def _fmt_attrs(char: Character) -> str:
    return "  ".join(f"{B.ATTRS[k]}{char.attributes.get(k, 0)}" for k in B.ATTR_KEYS)


def _trait_names(char: Character) -> str:
    ids = set(char.traits) | {t for t, s in char.genes.items() if s == 2}
    names = "、".join(T.trait_name(t) for t in sorted(ids))
    return names or "无"


def _char_panel(world, char: Optional[Character]) -> str:
    if char is None:
        return "（无人物）"
    gender = "♂" if char.gender == "male" else "♀"
    edu = f"  {T.education_name(char.education)}" if char.education else ""
    state = "在世" if char.is_alive else "已故"
    spouse = world.name_of(char.spouse) if char.spouse else "未婚"
    preg = "  怀孕中" if char.is_pregnant else ""
    return (
        f"[b]{char.name}[/b]  {world.dynasty_name_of(char.id)}\n"
        f"{gender} {char.age}岁  {state}{edu}\n"
        f"健康：{char.health_tier}（{char.health:.2f}）\n"
        f"{_fmt_attrs(char)}\n"
        f"特质：{_trait_names(char)}\n"
        f"金钱 {char.money:.0f}  威望 {char.prestige:.0f}  虔诚 {char.piety:.0f}\n"
        f"配偶：{spouse}{preg}\n"
        f"子女 {len(char.children)}"
    )


def _node_label(char: Character) -> Text:
    gender = "♂" if char.gender == "male" else "♀"
    text = f"{gender} {char.name}（{char.age}岁）"
    if char.is_alive:
        return Text(text)
    return Text(text, style="strike dim")


def _played_label(year: int, month: int, xun: int) -> str:
    total = ((year - B.START_YEAR) * B.MONTHS_PER_YEAR + (month - 1)) * B.XUN_PER_MONTH + xun
    y, rem = divmod(total, B.MONTHS_PER_YEAR * B.XUN_PER_MONTH)
    m, q = divmod(rem, B.XUN_PER_MONTH)
    return f"已游玩 {y}年{m}月{q}旬"


class MainScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self.viewing_id: Optional[int] = None
        self.show_played = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="left", classes="col"):
                yield Static(id="char_info")
                with Horizontal(id="left_actions"):
                    yield Button("家族树", id="family")
                    yield Button("✕", id="char_close", classes="sq")
            with VerticalScroll(id="mid", classes="col"):
                yield Static(id="events")
            with Vertical(id="right", classes="col"):
                yield Static(id="reserved")
                with Horizontal(id="right_actions"):
                    yield Button("婚配", id="marry")
                    yield Button("存档", id="save")
                    yield Button("读档", id="load")
                    yield Button("退出", id="quit")
                with Horizontal(id="timebar"):
                    yield Static(id="time")
                    yield Button("旬", id="tick_xun", classes="square")
                    yield Button("年", id="tick_year", classes="square")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_view()

    def on_screen_resume(self) -> None:
        self.refresh_view()

    def refresh_view(self) -> None:
        self.refresh_char()
        self.refresh_time()
        log = self.app.world.log[-40:]
        self.query_one("#events", Static).update("\n".join(reversed(log)) or "（尚无大事发生）")

    def refresh_char(self) -> None:
        world = self.app.world
        cid = self.viewing_id if self.viewing_id is not None else world.player_id
        self.query_one("#char_info", Static).update(_char_panel(world, world.get(cid)))
        self.query_one("#char_close").display = self.viewing_id is not None

    def refresh_time(self) -> None:
        d = self.app.world.date
        label = _played_label(d.year, d.month, d.xun) if self.show_played else d.label()
        self.query_one("#time", Static).update(label)

    def on_click(self, event: events.Click) -> None:
        if getattr(event.widget, "id", None) == "time":
            self.show_played = not self.show_played
            self.refresh_time()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "tick_xun":
            sim.tick_xun(self.app.world)
        elif bid == "tick_year":
            sim.advance(self.app.world, B.XUN_PER_MONTH * B.MONTHS_PER_YEAR)
        elif bid == "family":
            self.app.push_screen(FamilyTreeScreen())
            return
        elif bid == "char_close":
            self.viewing_id = None
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
    def __init__(self) -> None:
        super().__init__()
        self.viewing_id: Optional[int] = None
        self._line_ids: set[int] = set()
        self._expand_ids: set[int] = set()

    def compose(self) -> ComposeResult:
        with Horizontal(id="tree_root"):
            with Vertical(id="tree_info", classes="col"):
                yield Static(id="tree_char")
                yield Button("✕ 关闭", id="tree_close")
            with Vertical(id="tree_pane", classes="col"):
                yield Tree("家族树", id="tree")
                yield Button("返回主界面", id="tree_back")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#tree_info").display = False
        world = self.app.world
        world.refresh_ages()
        tree = self.query_one("#tree", Tree)
        player = world.player
        if player is None:
            tree.root.label = "（无家主）"
            return
        root = self._paternal_root(world, player)
        self._line_ids = self._line_to(world, player)
        grandkids: set[int] = set()
        for cid in player.children:
            child = world.get(cid)
            if child is not None:
                grandkids |= set(child.children)
        self._expand_ids = self._line_ids | set(player.children) | grandkids
        tree.root.label = _node_label(root)
        tree.root.data = root.id
        self._add_branch(world, root, tree.root)
        tree.root.expand()

    def _paternal_root(self, world, player: Character) -> Character:
        node = player
        seen = {player.id}
        while node.father is not None:
            nxt = world.get(node.father)
            if nxt is None or nxt.id in seen:
                break
            seen.add(nxt.id)
            node = nxt
        return node

    def _line_to(self, world, player: Character) -> set[int]:
        ids: set[int] = set()
        node: Optional[Character] = player
        while node is not None and node.id not in ids:
            ids.add(node.id)
            node = world.get(node.father) if node.father is not None else None
        return ids

    def _add_branch(self, world, char: Character, node, depth: int = 0) -> None:
        if depth > 12:
            return
        for cid in char.children:
            child = world.get(cid)
            if child is None:
                continue
            sub = node.add(_node_label(child), data=child.id)
            self._add_branch(world, child, sub, depth + 1)
            if child.id in self._expand_ids:
                sub.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        cid = event.node.data
        if cid is None:
            return
        self.viewing_id = cid
        self.query_one("#tree_info").display = True
        self.query_one("#tree_char", Static).update(_char_panel(self.app.world, self.app.world.get(cid)))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "tree_close":
            self.viewing_id = None
            self.query_one("#tree_info").display = False
        elif bid == "tree_back":
            self.app.pop_screen()


class MarriageScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Static("[b]选择一位婚配对象[/b]（仅显示可婚配者）")
        with VerticalScroll(id="marry_list"):
            player = self.app.world.player
            cands = marriage.candidates(self.app.world, player.id) if player else []
            if not cands:
                yield Static("（暂无可婚配对象；可推进时间等新的人成年）")
            for c in cands:
                dyn = self.app.world.dynasty_name_of(c.id)
                gender = "♂" if c.gender == "male" else "♀"
                yield Button(
                    f"{gender} {c.name} · {dyn} · {c.age}岁 · {_fmt_attrs(c)}", id=f"m_{c.id}"
                )
        yield Button("返回", id="marry_back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "marry_back":
            self.app.pop_screen()
            return
        if bid.startswith("m_"):
            player = self.app.world.player
            if player is None:
                return
            if marriage.arrange_marriage(self.app.world, player.id, int(bid[2:])):
                self.app.notify("婚姻达成")
                self.app.pop_screen()
            else:
                self.app.notify("无法成婚", severity="warning")


class HouseApp(App):
    CSS = """
    Screen { layout: vertical; }
    #main { height: 1fr; }
    .col { height: 1fr; border: round $primary; padding: 0 1; }
    #left { width: 1fr; }
    #mid { width: 1fr; }
    #right { width: 1fr; }
    #char_info { height: 1fr; }
    #left_actions { height: auto; }
    #reserved { height: 1fr; }
    #right_actions { layout: grid; grid-size: 2; grid-gutter: 0 1; height: auto; }
    #right_actions Button { width: 100%; }
    #timebar { height: 3; }
    #time { width: 1fr; height: 3; content-align: center middle; }
    .square { width: 5; height: 3; min-width: 5; padding: 0; }
    .sq { width: 5; min-width: 5; }
    #tree_root { height: 1fr; }
    #tree_info { width: 1fr; }
    #tree_pane { width: 2fr; }
    #tree { height: 1fr; }
    #marry_list { height: 1fr; }
    """

    def __init__(self, world=None):
        super().__init__()
        self.world = world or build_default_world()

    def on_mount(self) -> None:
        self.push_screen(MainScreen())


def run() -> None:
    HouseApp().run()
