# House · 王朝编年史

CK3 式中世纪家族王朝模拟器：1066 年的波希米亚，执掌普热梅斯利德家族，
看着血脉出生、起名、联姻、生育、衰老、继承 —— 别让家族绝嗣。

两种前端，共享同一套核心逻辑（`src/house/core/`）：

| | 命令 | 适合 |
|---|---|---|
| **横屏 TUI**（Textual） | `uv run python main.py` | 终端党 |
| **桌面 WebUI**（FastAPI + React） | `uv run python webui.py` | 电脑端日常游玩 |

## WebUI

「烛光宫廷」暗色主题。首次运行前需构建前端一次：

```bash
cd webui
bun install
bun run build
cd ..
uv run python webui.py            # 起服后自动开浏览器，默认 http://127.0.0.1:8000
```

前端热更开发（改 React 代码即时生效）：

```bash
# 终端 1
uv run python webui.py --dev --no-open     # 后端 API，开放 CORS
# 终端 2
cd webui && bun run dev                    # Vite 热更，http://localhost:5173
```

### 玩法要点

- **时间**：推一旬 / 推一年 / 自动推进（`空格` / `Y` / `A`）；出现新生儿时时间会被锁住，举行「命名礼」后继续。
- **编年史**（中栏）：结构化事件流，按类型筛选（有孕 / 诞生 / 联姻 / 成年 / 离世 / 继承），记事里的人名可点击查看。
- **人物卡**（左栏）：六维属性条上刻着潜力线；先天血脉区分显性与隐性携带者；体魄条 / 印象 / 眷属 / 子女一览。点击任何地方的人名即可切换人物。
- **家族**（右栏）：继承人预览、眷属上限（1/1）、天下人口（软上限 90 / 硬上限 160 会节流生育与婚配）、诸家威名、在世成员名录。
- **家族树**（`T`）：全屏可缩放谱系，婚姻连线、世代标尺、逝者标注。
- **终局**：家族绝嗣时展示存续之年、传承世代、生卒婚配统计；`?over-preview=1` 可随时预览该画面。

### 测试

```bash
uv run python tests/smoke.py        # 核心 + 存读档 + TUI 冒烟
uv run python tests/web_smoke.py    # WebUI API 全流程
```

### 打包（PyInstaller，可选）

WebUI 前端产物 `webui/dist` 需一并打进数据目录：在 spec 的 `datas` 中加
`('webui/dist', 'webui/dist')`；服务端会从 `sys._MEIPASS/webui/dist` 读取。

## 技术结构

```
src/house/core/   游戏逻辑（纯 Python，无 UI 依赖）：sim 生育 婚姻 遗传 健康 继承 存档
src/house/web/    FastAPI 桥：server.py（API）+ presenter.py（快照适配层，前后端唯一边界）
src/house/ui/     Textual TUI
webui/            React + TS 前端（bun 管理；zustand 状态；程序化纹章；SVG 家族树）
```

存档格式 v2：在 v1 基础上增加结构化 `events`（旧档读取时自动从字符串日志合成，双向兼容）。
数值调校见 `tools/sim_balance.py`；开发记录见 `WORK1.md`。
