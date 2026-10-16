# House - 受 ck3 启发的中世纪家族模拟器
> ⚠ 本 repo 重度 vibe coding 警告

**技术栈**：以 Python + FastAPI 为后端、TypeScript 为前端的中世纪家族模拟器。
**内容**：受 ck3 启发。力求还原 ck3。**尚十分稚嫩**。当前实现仅限生育·教育·婚姻。

**注：本作非 Paradox 官方作品，与 Paradox Interactive、Crusader Kings 系列无任何关联。**
## 玩法要点

见[教程文档](./docs/tutorial.md)

## 快速开始
### 通过发布版游玩
确保系统：Win11.

[Releases](https://github.com/Caesium-Inaba/house/releases) 下有发布包，建议下载最新版体验。

### 从零构建
**克隆仓库**
```bash
git clone https://github.com/Caesium-Inaba/house.git
cd house
```

**选用 WebUI** *（源码内有 tui 设计，但现已放弃维护）*
首次运行前需构建前端一次：

```bash
cd webui
bun install
bun run build
cd ..
```
**开始运行**
```bash
uv run python webui.py            
uv run python webui.py --debug   # 以 debug 模式启动游戏
```
起服后自动开浏览器，默认 http://127.0.0.1:8000

**前端热更开发**（改 React 代码即时生效）：

```bash
# 终端 1
uv run python webui.py --dev --no-open     # 后端 API，开放 CORS
# 终端 2
cd webui && bun run dev                    # Vite 热更，http://localhost:5173
```

### 模组（CK3 式）

模组放在与存档同级的 `mods/` 目录（exe 下即 exe 同目录），每个模组一个文件夹：

```
mods/
  我的模组/
    mod.json          # {"name", "version", "supported_version", "tags": [...]}
    data/traits.json  # 可选：按键深合并进同名原版数据（数组/标量整值覆盖）
    data/names.json   # 可选：名字池/新文化，合并语义同上
    localization/
      zh.json         # 可选：按 key 覆盖原版语言包
```

启用清单存在同目录的 `launcher.json`（`{"enabled": ["文件夹A", "文件夹B"]}`）。
载入顺序＝清单顺序：**从上往下，越靠下越优先**（对齐 CK3 启动器语义）。启动器
页面（首启自动落在那里，也可手动访问 `#/launcher`）里勾选启用、调整顺序后
「开始游戏」；改动随时生效于下一次开局，当前对局不变。可改内容：语言包、
特质数值（含新增特质条目）、名字池/新文化；事件与系统逻辑、`balance.py`
数值是代码，暂不可 mod。仓库内置示例模组见 `mod/example/`。

### 测试

```bash
uv run python tests/smoke.py        # 核心 + 存读档 + TUI 冒烟
uv run python tests/web_smoke.py    # WebUI API 全流程
```

## LICENSE
[MIT许可证](LICENSE)