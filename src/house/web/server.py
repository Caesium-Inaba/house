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

from .. import balance as B
from ..core import marriage, save, sim
from ..core.scenario import build_default_world
from ..core.world import World
from .presenter import build_snapshot, marriage_candidate_list

XUNS_PER_YEAR = 3 * 12


class TickBody(BaseModel):
    unit: str = "xun"  # xun / year


class NamingBody(BaseModel):
    child_id: int
    name: str


class MarriageBody(BaseModel):
    target_id: int


class SaveBody(BaseModel):
    name: str
    overwrite: bool = False


class LoadBody(BaseModel):
    name: str


class NewBody(BaseModel):
    seed: Optional[int] = None


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


def create_app(dev: bool = False, open_browser: Optional[str] = None) -> FastAPI:
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

    state: dict = {"world": None}

    def world() -> World:
        if state["world"] is None:
            state["world"] = build_default_world()
        return state["world"]

    def snap() -> dict:
        return build_snapshot(world())

    @app.get("/api/state")
    async def get_state() -> dict:
        return snap()

    @app.post("/api/new")
    async def new_game(body: NewBody) -> dict:
        state["world"] = build_default_world(body.seed)
        return {"ok": True, "message": "新的篇章开始了", "state": snap()}

    @app.post("/api/tick")
    async def tick(body: TickBody) -> dict:
        w = world()
        if not w.over:
            if body.unit == "year":
                sim.advance(w, XUNS_PER_YEAR, stop_on_naming=True)
            else:
                sim.tick_xun(w)
        return {"ok": True, "message": None, "state": snap()}

    @app.post("/api/naming")
    async def naming(body: NamingBody) -> dict:
        w = world()
        idx = next(
            (i for i, e in enumerate(w.naming_queue) if e.get("child_id") == body.child_id), None
        )
        if idx is None:
            raise HTTPException(400, "该孩子不在待命名队列中")
        name = body.name.strip()[:12]
        if not name:
            raise HTTPException(400, "名字不能为空")
        child = w.get(body.child_id)
        if child is None:
            raise HTTPException(400, "找不到该孩子")
        child.name = name
        w.naming_queue.pop(idx)
        return {"ok": True, "message": f"孩子得名「{name}」", "state": snap()}

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
            return {"ok": False, "message": "没有家主", "state": snap()}
        if player.spouse is not None:
            return {
                "ok": False,
                "message": f"已达眷属上限：配偶 {1}/{B.CONSORT_LIMIT}",
                "state": snap(),
            }
        ok = marriage.arrange_marriage(w, player.id, body.target_id)
        return {
            "ok": ok,
            "message": "姻缘缔结" if ok else "无法缔结这门婚事",
            "state": snap(),
        }

    @app.get("/api/saves")
    async def get_saves() -> dict:
        return {"ok": True, "saves": _saves_payload()}

    @app.post("/api/save")
    async def do_save(body: SaveBody) -> dict:
        name = body.name.strip()[:24] or save.default_name(world())
        if save.save_exists(name) and not body.overwrite:
            return {
                "ok": False,
                "message": "同名存档已存在",
                "exists": True,
                "saves": _saves_payload(),
            }
        save.save_named(world(), name)
        return {"ok": True, "message": f"已保存「{name}」", "saves": _saves_payload()}

    @app.post("/api/load")
    async def do_load(body: LoadBody) -> dict:
        path = save.save_path_for(body.name)
        if not path.is_file():
            raise HTTPException(404, "找不到该存档")
        state["world"] = save.load_world(path)
        return {"ok": True, "message": f"已读取「{body.name}」", "state": snap()}

    @app.delete("/api/saves/{name}")
    async def delete_save(name: str) -> dict:
        path = save.save_path_for(name)
        if path.is_file():
            path.unlink()
        return {"ok": True, "message": f"已删除「{name}」", "saves": _saves_payload()}

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
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    app = create_app(dev=args.dev, open_browser=None if (args.dev or args.no_open) else url)
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
