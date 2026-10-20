# House · 项目约定

- **TUI 已弃用，不再维护。** 时间系统改为公历一日一回合后，`src/house/ui/` 与 `main.py` 仅作历史遗留保留；不要为它添加新功能、修 bug 或适配新机制，所有界面工作只做 WebUI（`webui/` + `src/house/web/`）。
- 测试以 `tests/smoke.py`（核心）与 `tests/web_smoke.py`（WebUI API）为准；TUI 冒烟已移除。
