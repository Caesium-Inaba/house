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

### 时间与语言

时间以**日**为一回合，采用现代公历（含闰年）。推一日／推一月／推一年，或开自动推进（五档流速，空格暂停）。
岁数与成长精确到生日：孩子在自己的生日当天长大、开蒙、行成年礼。

界面支持**中文 / English** 随时切换（启动器与游戏内都有开关），编年史里的历史事件也会随语言整体重排；
历史家族名有英文译名（Přemyslid、Piast 等），人物名保留原文。

存档会记录游戏版本与启用的模组。版本或模组对不上的存档在档案室里会亮**红色感叹号**，悬停可看具体差异；
旧格式存档（0.2 及以前）不再兼容，请开新局。

### 压力与决议

压力 0–400，跨 100/200/300 各降一档（生育力 −10%/−30%/−50%，后两档健康 −1/−2）。首次跨档触发**精神崩溃**（5 年最多一次）：事件里可二选一拿特质并减压，或咬牙硬撑；特质池既有酗酒、自笞这类负担，也有**倾诉者、日记、健体**这三个纯正面特质（全部 +20% 减压并解锁专属决议）。压力到 400 时强制三级崩溃并清 100 压力。

压力来源：亲人离世（配偶/子女/父母 30，兄弟姐妹 20，祖孙 15），以及监护人替孩子定天性（20）。所有增减都受性格特质修正（慈悲更易累积、冷静/懒惰等更易消解）。

顶栏「决议」：日常减压（狩猎/宴饮/朝圣/静修，花费金钱/威望/虔诚）与应对机制解锁的专属动作，全部按天冷却。玩家扮演的角色死亡时会弹出「家主去世」通知，确认后由继承人接掌。

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
「开始游戏」；改动随时生效于下一次开局，当前对局不变。可改内容：语言包（`localization/zh.json` 或 `en.json`）、
特质数值（含新增特质条目）、名字池/新文化；事件与系统逻辑、`balance.py`
数值是代码，暂不可 mod。仓库内置示例模组见 `mod/example/`。

### 测试

```bash
uv run python tests/smoke.py        # 核心 + 存读档 + 模组
uv run python tests/web_smoke.py    # WebUI API 全流程
```

## LICENSE
[MIT许可证](LICENSE)