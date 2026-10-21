"""WebUI 宿主：FastAPI 托管游戏核心（进程内）与前端静态资源。

游戏是回合制、全同步：所有端点 async def 直调同步 core，
单事件循环串行执行，无需加锁。
"""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .. import VERSION_NAME, VERSION_NAME_EN, __version__
from .. import balance as B
from .. import i18n
from ..core import artifacts as artifacts_core
from ..core import decisions as decisions_core
from ..core import genetics, health, legacy, marriage, mods as mods_core, save, sim, stress as stress_core
from ..core import traits as T
from ..core.scenario import build_default_world
from ..core.time import Date, is_leap, month_days
from ..core.world import World
from .presenter import (
    betrothal_pools_payload,
    build_snapshot,
    marriage_candidate_list,
)


class TickBody(BaseModel):
    unit: str = "day"  # day / month / year


class NamingBody(BaseModel):
    child_id: int
    name: str


class MarriageBody(BaseModel):
    target_id: int


class TutoringBody(BaseModel):
    child_id: int
    focus: str
    guardian_id: Optional[int] = None


class TraitPickBody(BaseModel):
    child_id: int
    trait: str


class BetrothalBody(BaseModel):
    a_id: int
    b_id: int
    patrilineal: bool = True


class LegacyBody(BaseModel):
    tree: str


class SaveBody(BaseModel):
    name: str
    overwrite: bool = False


class LoadBody(BaseModel):
    name: str


class NewBody(BaseModel):
    seed: Optional[int] = None


class LauncherConfigBody(BaseModel):
    enabled: list[str] = []
    language: Optional[str] = None


class LauncherStartBody(BaseModel):
    enabled: list[str] = []
    load: Optional[str] = None
    language: Optional[str] = None


class SettingsBody(BaseModel):
    language: Optional[str] = None


class DecisionBody(BaseModel):
    id: str


class StressBreakBody(BaseModel):
    char_id: int
    trait: Optional[str] = None


class NoticeDismissBody(BaseModel):
    kind: str


class DebugStressBody(BaseModel):
    target_id: int
    amount: int = 50


class ArtifactBody(BaseModel):
    uid: int


class ArtifactGiftBody(BaseModel):
    uid: int
    target_id: int


class GuardianBody(BaseModel):
    child_id: int
    guardian_id: Optional[int] = None


class SelfRenameBody(BaseModel):
    name: str


class DynastyRenameBody(BaseModel):
    name: str


def _dist_dir() -> Optional[Path]:
    for candidate in (
        os.environ.get("HOUSE_WEBUI_DIST"),
        Path(sys._MEIPASS) / "webui" / "dist" if hasattr(sys, "_MEIPASS") else None,  # PyInstaller
        Path(__file__).resolve().parents[3] / "webui" / "dist",  # 仓库内开发
    ):
        if candidate and (Path(candidate) / "index.html").is_file():
            return Path(candidate)
    return None


def _saves_payload() -> list[dict]:
    saves = save.list_saves()
    for s in saves:
        s["path"] = str(s["path"])
    return saves


def create_app(dev: bool = False, open_browser: Optional[str] = None, debug: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        save.migrate_legacy()
        state["world"] = build_default_world()
        if open_browser:
            webbrowser.open(open_browser)
        yield

    app = FastAPI(title="House WebUI", docs_url=None, redoc_url=None, lifespan=lifespan)
    if dev:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    state: dict = {"world": None, "debug": debug, "lang": mods_core.load_config()["language"]}

    @app.middleware("http")
    async def _language_middleware(request, call_next):
        i18n.set_language(state.get("lang", "zh"))
        return await call_next(request)

    def world() -> World:
        if state["world"] is None:
            state["world"] = build_default_world()
        return state["world"]

    def snap() -> dict:
        payload = build_snapshot(world())
        payload["debug"] = bool(state.get("debug"))
        return payload

    @app.get("/api/state")
    async def get_state() -> dict:
        return snap()

    @app.post("/api/new")
    async def new_game(body: NewBody) -> dict:
        state["world"] = build_default_world(body.seed)
        return {"ok": True, "message": i18n.t("api.new_game"), "state": snap()}

    @app.post("/api/tick")
    async def tick(body: TickBody) -> dict:
        w = world()
        if not w.over:
            cur = w.date
            if body.unit == "year":
                # 精确推一年：落到明年的今天（2/29 遇平年退到 2/28）
                ny, nm, nd = cur.year + 1, cur.month, cur.day
                if nm == 2 and nd == 29 and not is_leap(ny):
                    nd = 28
                target = Date(ny, nm, nd)
                # 备份（旧行为）：stop_on_naming=True = 事件弹出即停（阻塞时间）。
                # 事件窗口化后事件不再阻塞推进；恢复阻塞式改回 True 即可。
                sim.advance(w, target.ordinal() - cur.ordinal(), stop_on_naming=False)
            elif body.unit == "month":
                ny, nm = (cur.year + 1, 1) if cur.month == 12 else (cur.year, cur.month + 1)
                target = Date(ny, nm, min(cur.day, month_days(ny, nm)))
                sim.advance(w, target.ordinal() - cur.ordinal(), stop_on_naming=False)
            else:
                sim.tick_day(w)
        return {"ok": True, "message": None, "state": snap()}

    @app.post("/api/naming")
    async def naming(body: NamingBody) -> dict:
        w = world()
        idx = next(
            (i for i, e in enumerate(w.naming_queue) if e.get("child_id") == body.child_id), None
        )
        if idx is None:
            raise HTTPException(400, i18n.t("api.not_in_naming"))
        name = body.name.strip()[:12]
        if not name:
            raise HTTPException(400, i18n.t("api.name_empty"))
        child = w.get(body.child_id)
        if child is None:
            raise HTTPException(400, i18n.t("api.invalid_child"))
        w.rename_character(child.id, name)
        w.naming_queue.pop(idx)
        return {"ok": True, "message": i18n.t("api.named", name=name), "state": snap()}

    @app.get("/api/marriage/candidates")
    async def get_candidates() -> dict:
        w = world()
        player = w.player
        if player is None:
            return {"ok": False, "candidates": []}
        return {"ok": True, "candidates": marriage_candidate_list(w, player.id)}

    @app.post("/api/marriage")
    async def arrange(body: MarriageBody) -> dict:
        w = world()
        player = w.player
        if player is None:
            return {"ok": False, "message": i18n.t("api.no_player"), "state": snap()}
        if player.spouse is not None:
            return {
                "ok": False,
                "message": i18n.t("api.consort_limit", n=1, limit=B.CONSORT_LIMIT),
                "state": snap(),
            }
        ok = marriage.arrange_marriage(w, player.id, body.target_id)
        return {
            "ok": ok,
            "message": i18n.t("api.married") if ok else i18n.t("api.marriage_denied"),
            "state": snap(),
        }

    @app.get("/api/betrothal/pools")
    async def get_betrothal_pools() -> dict:
        return {"ok": True, **betrothal_pools_payload(world())}

    @app.post("/api/betrothal")
    async def do_betrothal(body: BetrothalBody) -> dict:
        w = world()
        ok = marriage.arrange_betrothal(w, body.a_id, body.b_id, patrilineal=body.patrilineal)
        return {
            "ok": ok,
            "message": i18n.t("api.betrothed") if ok else i18n.t("api.betrothal_denied"),
            "state": snap(),
        }

    @app.post("/api/tutoring")
    async def do_tutoring(body: TutoringBody) -> dict:
        w = world()
        child = w.get(body.child_id)
        if child is None:
            raise HTTPException(400, i18n.t("api.invalid_child"))
        idx = next(
            (i for i, e in enumerate(w.tutoring_queue) if e.get("child_id") == body.child_id), None
        )
        if idx is None:
            raise HTTPException(400, i18n.t("api.not_in_tutoring"))
        if body.focus not in B.ATTRS:
            raise HTTPException(400, i18n.t("api.unknown_focus"))
        guardian = w.get(body.guardian_id)
        child.education_focus = body.focus
        child.guardian = guardian.id if guardian is not None else None
        w.tutoring_queue.pop(idx)
        message = genetics.add_tutoring_event(w, child, body.focus, guardian)
        return {"ok": True, "message": message, "state": snap()}

    @app.post("/api/traitpick")
    async def do_traitpick(body: TraitPickBody) -> dict:
        w = world()
        child = w.get(body.child_id)
        if child is None:
            raise HTTPException(400, i18n.t("api.invalid_child"))
        idx = next(
            (i for i, e in enumerate(w.trait_queue) if e.get("child_id") == body.child_id), None
        )
        if idx is None:
            raise HTTPException(400, i18n.t("api.not_in_traitpick"))
        if body.trait not in T.PERSONALITY:
            raise HTTPException(400, i18n.t("api.unknown_trait"))
        genetics.apply_trait_pick(w, child, body.trait)
        w.trait_queue.pop(idx)
        return {"ok": True, "message": i18n.t("api.trait_set", trait=T.trait_name(body.trait)), "state": snap()}

    @app.post("/api/rename")
    async def rename(body: NamingBody) -> dict:
        """给任意未满周岁的新生儿改名（不限宗族）。"""
        w = world()
        child = w.get(body.child_id)
        if child is None:
            raise HTTPException(400, i18n.t("api.no_such_person"))
        if not child.is_alive or child.age >= 1:
            raise HTTPException(400, i18n.t("api.too_old_to_rename"))
        name = body.name.strip()[:12]
        if not name:
            raise HTTPException(400, i18n.t("api.name_empty"))
        w.rename_character(child.id, name)
        return {"ok": True, "message": i18n.t("api.renamed", name=name), "state": snap()}

    @app.post("/api/suicide")
    async def suicide() -> dict:
        """调试用自杀：立即结束家主生命（正常/调试模式均可用）。"""
        w = world()
        player = w.player
        if player is None or not player.is_alive or w.over:
            return {"ok": False, "message": i18n.t("api.no_living_head"), "state": snap()}
        from ..core import inheritance

        health.kill(w, player, "suicide")
        inheritance.handle_player_death(w)
        return {"ok": True, "message": i18n.t("api.suicide"), "state": snap()}

    @app.post("/api/debug/kill")
    async def debug_kill(body: MarriageBody) -> dict:
        """仅 --debug 模式：指名杀人，死因=调试。"""
        if not state.get("debug"):
            raise HTTPException(403, i18n.t("api.need_debug"))
        w = world()
        target = w.get(body.target_id)
        if target is None or not target.is_alive:
            raise HTTPException(400, "目标不存在或已亡故")
        from ..core import inheritance

        health.kill(w, target, "debug")
        if target.id == w.player_id:
            inheritance.handle_player_death(w)
        return {"ok": True, "message": i18n.t("api.debug_kill", name=target.name), "state": snap()}

    @app.post("/api/legacy")
    async def do_legacy(body: LegacyBody) -> dict:
        w = world()
        player = w.player
        dyn = player.dynasty if player else None
        ok, msg = legacy.buy(w, dyn, body.tree)
        return {"ok": ok, "message": msg, "state": snap()}

    @app.get("/api/saves")
    async def get_saves() -> dict:
        return {"ok": True, "saves": _saves_payload()}

    @app.post("/api/save")
    async def do_save(body: SaveBody) -> dict:
        name = body.name.strip()[:24] or save.default_name(world())
        if save.save_exists(name) and not body.overwrite:
            return {
                "ok": False,
                "message": i18n.t("api.save_exists"),
                "exists": True,
                "saves": _saves_payload(),
            }
        save.save_named(world(), name)
        return {"ok": True, "message": i18n.t("ui.saved", name=name), "saves": _saves_payload()}

    @app.post("/api/load")
    async def do_load(body: LoadBody) -> dict:
        path = save.save_path_for(body.name)
        if not path.is_file():
            raise HTTPException(404, i18n.t("api.not_found"))
        try:
            state["world"] = save.load_world(path)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"ok": True, "message": i18n.t("api.loaded", name=body.name), "state": snap()}

    @app.delete("/api/saves/{name}")
    async def delete_save(name: str) -> dict:
        path = save.save_path_for(name)
        if path.is_file():
            path.unlink()
        return {"ok": True, "message": i18n.t("api.save_deleted", name=name), "saves": _saves_payload()}

    # ── 启动器（CK3 式：模组清单独立于游戏会话） ──

    def launcher_started(w: World) -> bool:
        """是否已经进入了游戏会话（启动器只在全新初始世界上出现）。"""
        return (w.date.year, w.date.month, w.date.day) != (1066, 1, 1) or w.over

    @app.get("/api/decisions")
    async def get_decisions() -> dict:
        w = world()
        player = w.player
        if player is None:
            return {"ok": False, "decisions": [], "message": i18n.t("api.no_player")}
        return {
            "ok": True,
            "decisions": decisions_core.list_for(w, player),
            "stress": player.stress,
            "max_stress": B.STRESS_MAX,
        }

    @app.post("/api/decision")
    async def do_decision(body: DecisionBody) -> dict:
        w = world()
        player = w.player
        if player is None or not player.is_alive:
            return {"ok": False, "message": i18n.t("api.no_living_head")}
        ok, key = decisions_core.apply(w, player, body.id)
        return {"ok": ok, "message": i18n.t(key), "state": snap()}

    @app.post("/api/stressbreak")
    async def do_stressbreak(body: StressBreakBody) -> dict:
        w = world()
        ok = stress_core.resolve_pending(w, body.char_id, body.trait)
        key = "api.stressbreak_done" if ok else "api.stressbreak_invalid"
        return {"ok": ok, "message": i18n.t(key), "state": snap()}

    @app.post("/api/notice/dismiss")
    async def dismiss_notice(body: NoticeDismissBody) -> dict:
        w = world()
        if body.kind == "death":
            w.death_notice = None
        return {"ok": True, "message": None, "state": snap()}

    @app.post("/api/debug/stress")
    async def debug_stress(body: DebugStressBody) -> dict:
        """仅 --debug：人为增加压力（验收/调试用）。"""
        if not state.get("debug"):
            raise HTTPException(403, i18n.t("api.need_debug"))
        w = world()
        stress_core.add_stress(w, body.target_id, body.amount, "debug")
        return {"ok": True, "message": None, "state": snap()}

    # ── 宝物 ──

    def _player_char(w: World):
        player = w.player
        if player is None or not player.is_alive:
            raise HTTPException(400, i18n.t("api.no_living_head"))
        return player

    @app.post("/api/artifact/equip")
    async def artifact_equip(body: ArtifactBody) -> dict:
        w = world()
        player = _player_char(w)
        ok = artifacts_core.equip(w, player, body.uid)
        return {"ok": ok, "message": i18n.t("api.artifact_equipped" if ok else "api.artifact_missing"), "state": snap()}

    @app.post("/api/artifact/unequip")
    async def artifact_unequip(body: ArtifactBody) -> dict:
        w = world()
        player = _player_char(w)
        ok = artifacts_core.unequip(w, player, body.uid)
        return {"ok": ok, "message": i18n.t("api.artifact_unequipped" if ok else "api.artifact_missing"), "state": snap()}

    @app.post("/api/artifact/destroy")
    async def artifact_destroy(body: ArtifactBody) -> dict:
        w = world()
        player = _player_char(w)
        ok, _gold = artifacts_core.destroy(w, player, body.uid)
        return {"ok": ok, "message": i18n.t("api.artifact_destroyed" if ok else "api.artifact_missing"), "state": snap()}

    @app.post("/api/artifact/reforge")
    async def artifact_reforge(body: ArtifactBody) -> dict:
        w = world()
        player = _player_char(w)
        ok, key = artifacts_core.reforge(w, player, body.uid)
        return {"ok": ok, "message": i18n.t(key), "state": snap()}

    @app.post("/api/artifact/gift")
    async def artifact_gift(body: ArtifactGiftBody) -> dict:
        w = world()
        player = _player_char(w)
        target = w.get(body.target_id)
        if target is None:
            raise HTTPException(400, i18n.t("api.no_such_person"))
        ok, key = artifacts_core.gift(w, player, target, body.uid)
        return {"ok": ok, "message": i18n.t(key), "state": snap()}

    # ── 监护关系（家主可随时指定/更换/解除） ──

    @app.post("/api/guardian")
    async def set_guardian(body: GuardianBody) -> dict:
        w = world()
        player = _player_char(w)
        child = w.get(body.child_id)
        if child is None or not child.is_alive:
            raise HTTPException(400, i18n.t("api.invalid_child"))
        if child.id == player.id or child.age >= B.CHILDHOOD_END or child.dynasty != player.dynasty:
            raise HTTPException(400, i18n.t("api.guardian_child_invalid"))
        if body.guardian_id is None:
            child.guardian = None
            return {"ok": True, "message": i18n.t("api.guardian_cleared"), "state": snap()}
        guardian = w.get(body.guardian_id)
        if (
            guardian is None
            or not guardian.is_alive
            or guardian.age < B.CHILDHOOD_END
            or guardian.dynasty != player.dynasty
            or guardian.id == child.id
        ):
            raise HTTPException(400, i18n.t("api.guardian_invalid"))
        child.guardian = guardian.id
        message = i18n.t("api.guardian_set", child=child.name, guardian=guardian.name)
        return {"ok": True, "message": message, "state": snap()}

    # ── 改名：玩家自己（任意年龄）与宗族（家主） ──

    @app.post("/api/rename_self")
    async def rename_self(body: SelfRenameBody) -> dict:
        w = world()
        player = _player_char(w)
        name = body.name.strip()[:12]
        if not name:
            raise HTTPException(400, i18n.t("api.name_empty"))
        w.rename_character(player.id, name)
        return {"ok": True, "message": i18n.t("api.renamed", name=name), "state": snap()}

    @app.post("/api/dynasty/rename")
    async def rename_dynasty(body: DynastyRenameBody) -> dict:
        w = world()
        player = _player_char(w)
        if player.dynasty is None:
            raise HTTPException(400, i18n.t("api.no_dynasty"))
        dyn = w.dynasties.get(player.dynasty)
        if dyn is None or dyn.head != player.id:
            raise HTTPException(400, i18n.t("api.rename_dynasty_forbidden"))
        name = body.name.strip()[:16]
        if not name:
            raise HTTPException(400, i18n.t("api.name_empty"))
        w.rename_dynasty(player.dynasty, name)
        return {"ok": True, "message": i18n.t("api.dynasty_renamed", name=name), "state": snap()}

    @app.post("/api/settings")
    async def update_settings(body: SettingsBody) -> dict:
        """切换展示语言（现阶段立即全量重渲染；restart_required 为将来的重启式切换预留）。"""
        if body.language is not None:
            if body.language not in ("zh", "en"):
                raise HTTPException(400, i18n.t("api.unknown_language"))
            state["lang"] = body.language
            mods_core.save_config(mods_core.load_config()["enabled"], language=body.language)
        i18n.set_language(state["lang"])
        return {"ok": True, "message": None, "restart_required": False, "state": snap()}

    @app.get("/api/launcher")
    async def launcher_state() -> dict:
        from ..core import mods as mods_core

        infos = [info.__dict__ for info in mods_core.scan()]
        enabled = mods_core.load_config()["enabled"]
        for info in infos:
            info["order"] = enabled.index(info["folder"]) if info["folder"] in enabled else -1
        return {
            "ok": True,
            "started": launcher_started(world()),
            "mods": infos,
            "enabled": enabled,
            "language": state["lang"],
            "game_version": __version__,
            "version_names": {"zh": VERSION_NAME, "en": VERSION_NAME_EN},
        }

    @app.post("/api/launcher/config")
    async def launcher_config(body: LauncherConfigBody) -> dict:
        from ..core import mods as mods_core

        root = mods_core.mods_root()
        for folder in body.enabled:
            if not (root / folder).is_dir():
                raise HTTPException(400, i18n.t("api.unknown_mod", folder=folder))
        mods_core.save_config(body.enabled, language=body.language)
        if body.language is not None:
            state["lang"] = body.language
        return {"ok": True, "enabled": body.enabled}

    @app.post("/api/launcher/start")
    async def launcher_start(body: LauncherStartBody) -> dict:
        """按启用清单激活模组并开新局（或读取存档）。"""
        from ..core import mods as mods_core
        from ..core import traits as traits_core

        root = mods_core.mods_root()
        for folder in body.enabled:
            if not (root / folder).is_dir():
                raise HTTPException(400, i18n.t("api.unknown_mod", folder=folder))
        mods_core.save_config(body.enabled, language=body.language)
        if body.language is not None:
            state["lang"] = body.language
        traits_core.reload_data()
        if body.load:
            path = save.save_path_for(body.load)
            if not path.is_file():
                raise HTTPException(404, i18n.t("api.not_found"))
            try:
                state["world"] = save.load_world(path)
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
            message = i18n.t("api.modded_load", name=body.load)
        else:
            state["world"] = build_default_world()
            message = i18n.t("api.modded_new_game")
        return {"ok": True, "message": message, "state": snap()}


    dist = _dist_dir()
    if dist is not None:
        app.mount("/", StaticFiles(directory=dist, html=True), name="webui")
    else:
        @app.get("/")
        async def placeholder() -> FileResponse:
            hint = Path(__file__).with_name("placeholder.html")
            return FileResponse(hint, media_type="text/html")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="House WebUI 服务器")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--dev", action="store_true", help="开放 CORS（配合 Vite dev server）")
    parser.add_argument("--debug", action="store_true", help="调试模式：开放指名杀人等调试端点（不随 exe 打包启用）")
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/#/launcher"
    app = create_app(dev=args.dev, debug=args.debug, open_browser=None if (args.dev or args.no_open) else url)
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
