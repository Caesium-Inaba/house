"""WebUI 冒烟测试：API 全流程。

用法：uv run python tests/web_smoke.py
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from fastapi.testclient import TestClient  # noqa: E402

from house.web.server import create_app  # noqa: E402


def main() -> None:
    # 存档写入临时目录，避免污染仓库
    os.chdir(tempfile.mkdtemp(prefix="house_web_smoke_"))
    client = TestClient(create_app())

    # ── 状态 ──
    r = client.get("/api/state")
    assert r.status_code == 200, r.text
    snap = r.json()
    assert snap["player_id"] == 1
    assert snap["date"]["year"] == 1066
    assert snap["population"]["alive"] >= 8
    assert snap["characters"][0]["relation"] is not None
    assert snap["meta"]["consort_limit"] == 1
    assert any(e["type"] == "succession" for e in snap["events"])
    print("[state] OK  在世", snap["population"]["alive"], "人")

    # ── 减压决议：列表、执行与冷却 ──
    r = client.get("/api/decisions")
    assert r.status_code == 200 and r.json()["ok"]
    dec = {d["id"]: d for d in r.json()["decisions"]}
    assert {"hunt", "feast", "pilgrimage", "meditate"} <= set(dec), dec.keys()
    assert dec["meditate"]["available"] is True
    r = client.post("/api/decision", json={"id": "meditate"})
    assert r.json()["ok"], r.text
    r = client.get("/api/decisions")
    dec = {d["id"]: d for d in r.json()["decisions"]}
    assert dec["meditate"]["available"] is False and dec["meditate"]["reason"] == "cooldown"
    print("[decisions] OK  静修执行且进入冷却")

    # ── 调试加压：非 debug 模式拒绝 ──
    r = client.post("/api/debug/stress", json={"target_id": 1, "amount": 50})
    assert r.status_code == 403
    print("[debug stress off] OK  403 拒绝")

    # ── 语言切换：快照与历史事件全量重渲染 ──
    r = client.post("/api/settings", json={"language": "en"})
    res = r.json()
    assert res["ok"] and res["restart_required"] is False
    en_label = res["state"]["date"]["label"]
    assert "1966" not in en_label and ("January" in en_label or en_label.endswith("1066")), en_label
    assert any("becomes head of House Přemyslid" in e["text"] for e in res["state"]["events"]), res["state"]["events"][:2]
    r = client.post("/api/settings", json={"language": "zh"})
    assert any("弗拉季斯拉夫成为" in e["text"] for e in r.json()["state"]["events"])
    print("[i18n] OK  快照与历史事件随语言切换")

    # ── 推一日 ──
    before = snap["date"]
    r = client.post("/api/tick", json={"unit": "day"})
    assert r.status_code == 200
    snap = r.json()["state"]
    assert (snap["date"]["year"], snap["date"]["month"], snap["date"]["day"]) != (
        before["year"], before["month"], before["day"]
    )
    print("[tick day] OK")

    # ── 推年（stop_on_naming：可能停在起名事件）──
    r = client.post("/api/tick", json={"unit": "year"})
    snap = r.json()["state"]
    advanced = snap["date"]["year"] - before["year"]
    assert snap["naming_queue"] or snap["over"] or advanced >= 1, f"推年异常：{snap['date']}"
    print("[tick year] OK  推进到", snap["date"]["label"])

    # ── 起名（构造一个确定待命名场景：直接推年直到队列非空）──
    for _ in range(800):
        snap = client.post("/api/tick", json={"unit": "day"}).json()["state"]
        if snap["over"] or snap["naming_queue"]:
            break
    if snap["naming_queue"]:
        entry = snap["naming_queue"][0]
        # 改名前先抓出该婴儿的出生事件（text 里还是临时名）
        birth = next(
            (
                e
                for e in snap["events"]
                if e["type"] == "birth" and entry["child_id"] in e["actors"]
            ),
            None,
        )
        r = client.post("/api/naming", json={"child_id": entry["child_id"], "name": "测试之子"})
        assert r.status_code == 200
        res = r.json()
        assert res["ok"] and all(e["child_id"] != entry["child_id"] for e in res["state"]["naming_queue"])
        child = next(c for c in res["state"]["characters"] if c["id"] == entry["child_id"])
        assert child["name"] == "测试之子"
        # 改名应同步历史事件：出生事件的 text 已用新名（编年史里人名可点的前提）
        if birth is not None:
            new_birth = next(
                (
                    e
                    for e in res["state"]["events"]
                    if e["type"] == "birth" and entry["child_id"] in e["actors"]
                ),
                None,
            )
            assert new_birth is not None and "测试之子" in new_birth["text"], new_birth
        print("[naming] OK  命名", entry["suggested"], "-> 测试之子（出生事件已同步）")
    else:
        print("[naming] SKIP  未出现待命名（seed 相关）")

    # ── 婚配：玩家开局已有配偶，应被眷属上限拒绝 ──
    r = client.get("/api/marriage/candidates")
    assert r.status_code == 200
    cands = r.json()["candidates"]
    print("[candidates] OK  候选", len(cands), "人")
    r = client.post("/api/marriage", json={"target_id": cands[0]["id"] if cands else 999})
    res = r.json()
    assert not res["ok"] and "眷属上限" in res["message"]
    print("[marriage limit] OK  拒绝信息:", res["message"])

    # ── 存档 ──
    r = client.post("/api/save", json={"name": "冒烟测试档"})
    assert r.json()["ok"]
    r = client.post("/api/save", json={"name": "冒烟测试档"})
    assert not r.json()["ok"] and r.json()["exists"]
    r = client.post("/api/save", json={"name": "冒烟测试档", "overwrite": True})
    assert r.json()["ok"]
    saves = r.json()["saves"]
    assert any(s["name"] == "冒烟测试档" for s in saves)
    print("[save] OK  槽位", [s["name"] for s in saves])

    # ── 读档 ──
    r = client.post("/api/load", json={"name": "冒烟测试档"})
    res = r.json()
    assert res["ok"] and res["state"]["date"]["year"] == saves[0]["year"]
    print("[load] OK  回到", res["state"]["date"]["label"])

    # ── 删除存档 ──
    r = client.request("DELETE", "/api/saves/冒烟测试档")
    assert r.json()["ok"]
    assert not any(s["name"] == "冒烟测试档" for s in r.json()["saves"])
    print("[delete save] OK")

    # ── 新局 ──
    r = client.post("/api/new", json={"seed": 7})
    res = r.json()
    assert res["ok"] and res["state"]["date"]["year"] == 1066
    print("[new] OK")

    # ── 王朝传承：威名不足应被拒绝 ──
    r = client.post("/api/legacy", json={"tree": "blood"})
    res = r.json()
    assert not res["ok"] and "威名" in res["message"], res
    assert res["state"]["legacies"]["trees"][0]["cost"] == 500
    print("[legacy reject] OK ", res["message"])

    # ── 教养礼：推年直到 6 岁孩子进入队列，指派开蒙 ──
    for _ in range(1200):
        snap = client.post("/api/tick", json={"unit": "day"}).json()["state"]
        if snap["over"] or snap["tutoring_queue"]:
            break
    if snap["tutoring_queue"]:
        entry = snap["tutoring_queue"][0]
        guardians = entry["guardian_candidates"]
        gid = guardians[0]["id"] if guardians else None
        r = client.post(
            "/api/tutoring",
            json={"child_id": entry["child_id"], "focus": entry["suggested_focus"], "guardian_id": gid},
        )
        res = r.json()
        assert res["ok"], res
        assert next(
            (e for e in res["state"]["tutoring_queue"] if e["child_id"] == entry["child_id"]), None
        ) is None
        child = next(c for c in res["state"]["characters"] if c["id"] == entry["child_id"])
        assert child["education_focus"] == entry["suggested_focus"] and child["guardian"] == gid
        assert any(e["type"] == "tutoring" for e in res["state"]["events"])
        print("[tutoring] OK", res["message"])
    else:
        print("[tutoring] SKIP  12 年内无玩家血亲满 6 岁")

    # ── 婚约：订婚池 + 缔结 + 人物快照反映 ──
    snap = client.get("/api/state").json()
    r = client.get("/api/betrothal/pools")
    pools = r.json()
    own, other = pools["own"], pools["other"]
    print("[pools] OK  自家", len(own), "他人", len(other))
    pair = next(
        ((a, b) for a in own for b in other if a["gender"] != b["gender"]),
        None,
    )
    if pair:
        a, b = pair
        r = client.post("/api/betrothal", json={"a_id": a["id"], "b_id": b["id"], "patrilineal": False})
        res = r.json()
        assert res["ok"], res["message"]
        char = next(c for c in res["state"]["characters"] if c["id"] == a["id"])
        assert char["betrothed"]["name"] == b["name"]
        assert any(e["type"] == "betrothal" for e in res["state"]["events"])
        # 同对象再订应被拒绝
        other2 = [x for x in other if x["id"] != b["id"]]
        if other2:
            r = client.post("/api/betrothal", json={"a_id": a["id"], "b_id": other2[0]["id"]})
            assert not r.json()["ok"]
        print("[betrothal] OK", b["name"], "母系")
    else:
        print("[betrothal] SKIP  无异性可订孩子")

    # ── 性情抉择（9/12/15 岁） + 童年特质/转换存在性 ──
    snap = client.get("/api/state").json()
    kids = [c for c in snap["characters"] if c["alive"] and not c["is_adult"]]
    if not snap["trait_queue"] and kids:
        # 快进到第一个抉择点
        for _ in range(1200):
            s2 = client.post("/api/tick", json={"unit": "day"}).json()["state"]
            if s2["over"] or s2["trait_queue"]:
                snap = s2
                break
            if s2["naming_queue"]:
                e = s2["naming_queue"][0]
                snap = client.post("/api/naming", json={"child_id": e["child_id"], "name": e["suggested"]}).json()["state"]
            if s2["tutoring_queue"]:
                e = s2["tutoring_queue"][0]
                gid = e["guardian_candidates"][0]["id"] if e["guardian_candidates"] else None
                snap = client.post("/api/tutoring", json={"child_id": e["child_id"], "focus": e["suggested_focus"], "guardian_id": gid}).json()["state"]
    if snap["trait_queue"]:
        entry = snap["trait_queue"][0]
        assert entry["options"][0]["kind"] == "taught" and entry["options"][1]["kind"] == "stray"
        r = client.post("/api/traitpick", json={"child_id": entry["child_id"], "trait": entry["options"][0]["id"]})
        res = r.json()
        assert res["ok"], res
        child = next(c for c in res["state"]["characters"] if c["id"] == entry["child_id"])
        assert entry["options"][0]["id"] in [t["id"] for t in child["traits"]]
        print("[traitpick] OK", entry["name"], "->", entry["options"][0]["name"])
    else:
        print("[traitpick] SKIP  快进 12 年内无抉择点")
    # 世数展示抽查：display_name 字段存在
    assert all("display_name" in c for c in snap["characters"])
    print("[display_name] OK")

    # ── 新生儿通用改名（不限宗族，age<1） ──
    snap = client.get("/api/state").json()
    newborn = next((c for c in snap["characters"] if c["alive"] and c["age"] < 1), None)
    if newborn is None:
        for _ in range(800):
            s2 = client.post("/api/tick", json={"unit": "day"}).json()["state"]
            if s2["over"]:
                break
            if s2["naming_queue"]:
                e = s2["naming_queue"][0]
                s2 = client.post("/api/naming", json={"child_id": e["child_id"], "name": e["suggested"]}).json()["state"]
            if s2["tutoring_queue"]:
                e = s2["tutoring_queue"][0]
                gid = e["guardian_candidates"][0]["id"] if e["guardian_candidates"] else None
                s2 = client.post("/api/tutoring", json={"child_id": e["child_id"], "focus": e["suggested_focus"], "guardian_id": gid}).json()["state"]
            if s2["trait_queue"]:
                e = s2["trait_queue"][0]
                s2 = client.post("/api/traitpick", json={"child_id": e["child_id"], "trait": e["options"][1]["id"]}).json()["state"]
            snap = s2
            newborn = next((c for c in snap["characters"] if c["alive"] and c["age"] < 1), None)
            if newborn:
                break
    if newborn:
        r = client.post("/api/rename", json={"child_id": newborn["id"], "name": "调试名"})
        res = r.json()
        assert res["ok"] and next(c for c in res["state"]["characters"] if c["id"] == newborn["id"])["name"] == "调试名"
        print("[rename] OK")
    else:
        print("[rename] SKIP 无新生儿")

    # ── 旧版本存档：直接拒绝 ──
    import json as _json
    import pathlib as _pl
    _pl.Path("saves").mkdir(exist_ok=True)
    old = _json.loads(_pl.Path("saves").glob("*.json").__iter__().__next__().read_text(encoding="utf-8")) if list(_pl.Path("saves").glob("*.json")) else None
    # 若上面已有正常存档，复制并降级版本号；否则构造最小 v3 档
    if old is None:
        old = {"version": 3, "date": {"year": 1066, "month": 1, "xun": 0}, "characters": []}
    else:
        old = dict(old)
        old["version"] = 3
        old["date"] = {"year": 1066, "month": 1, "xun": 0}
        old["save_name"] = "旧档"
    _pl.Path("saves/旧档.json").write_text(_json.dumps(old, ensure_ascii=False), encoding="utf-8")
    r = client.post("/api/load", json={"name": "旧档"})
    assert r.status_code == 400 and "旧" in r.json()["detail"], r.text
    print("[old save] OK  旧版本存档被拒绝")

    # ── 启动器：扫描/启用清单校验/按清单开局 ──
    r = client.get("/api/launcher")
    assert r.status_code == 200 and r.json()["ok"]
    print("[launcher scan] OK  已装模组", len(r.json()["mods"]), "个")
    r = client.post("/api/launcher/config", json={"enabled": ["不存在_冒烟"]})
    assert r.status_code == 400
    r = client.post("/api/launcher/start", json={"enabled": []})
    res = r.json()
    assert res["ok"] and res["state"]["date"]["year"] == 1066
    snap = res["state"]
    r = client.get("/api/launcher")
    assert r.json()["started"] is False, "新局不该被视为已开局"
    client.post("/api/tick", json={"unit": "day"})
    r = client.get("/api/launcher")
    assert r.json()["started"] is True, "推旬后应视为已开局"
    print("[launcher start] OK  空清单开局正常，started 判定可以随进度发生")

    # ── 模组「计划生育」：宝物购买/装备/赠予/销毁 + 监护/改名 ──
    import pathlib as _pl
    import shutil as _sh
    repo = _pl.Path(__file__).resolve().parent.parent
    _pl.Path("mods").mkdir(exist_ok=True)
    _sh.copytree(repo / "mods" / "perfect-f-word", _pl.Path("mods") / "perfect-f-word")
    r = client.post("/api/launcher/start", json={"enabled": ["perfect-f-word"]})
    assert r.json()["ok"], r.text
    snap = r.json()["state"]
    opts = {o["id"]: o for o in snap["decision_options"]}
    assert "buy_condom" in opts and "buy_incense" in opts, opts.keys()
    assert opts["buy_condom"]["name"] == "购置避孕套", opts["buy_condom"]
    assert opts["buy_condom"]["group_label"] == "计生用具", opts["buy_condom"]
    money0 = next(c for c in snap["characters"] if c["id"] == snap["player_id"])["money"]

    r = client.post("/api/decision", json={"id": "buy_condom"})
    assert r.json()["ok"], r.text
    snap = r.json()["state"]
    me = next(c for c in snap["characters"] if c["id"] == snap["player_id"])
    assert me["money"] == money0 - 10
    condom = next(a for a in me["artifacts"] if a["def"] == "condom")
    assert condom["equipped"] and condom["slot"] == "armor" and condom["durability"] == 1
    assert condom["name"] == "避孕套"

    r = client.post("/api/decision", json={"id": "buy_incense"})
    snap = r.json()["state"]
    me = next(c for c in snap["characters"] if c["id"] == snap["player_id"])
    incense = next(a for a in me["artifacts"] if a["def"] == "incense")
    assert not incense["equipped"], "同槽不应自动替换"
    r = client.post("/api/artifact/equip", json={"uid": incense["uid"]})
    snap = r.json()["state"]
    me = next(c for c in snap["characters"] if c["id"] == snap["player_id"])
    worn = [a for a in me["artifacts"] if a["equipped"]]
    assert len(worn) == 1 and worn[0]["def"] == "incense", worn

    spouse_id = me["spouse"]
    r = client.post("/api/artifact/gift", json={"uid": condom["uid"], "target_id": spouse_id})
    assert r.json()["ok"], r.text
    snap = r.json()["state"]
    sp = next(c for c in snap["characters"] if c["id"] == spouse_id)
    assert any(a["def"] == "condom" for a in sp["artifacts"]), sp["artifacts"]
    me = next(c for c in snap["characters"] if c["id"] == snap["player_id"])
    assert not any(a["uid"] == condom["uid"] for a in me["artifacts"])

    money1 = me["money"]
    r = client.post("/api/artifact/destroy", json={"uid": incense["uid"]})
    assert r.json()["ok"], r.text
    snap = r.json()["state"]
    me = next(c for c in snap["characters"] if c["id"] == snap["player_id"])
    assert not any(a["uid"] == incense["uid"] for a in me["artifacts"])
    assert me["money"] == money1, "模组宝物销毁不返金"
    print("[artifacts api] OK  购买/装备槽位/赠予/销毁不返金")

    # 监护：家主指定 → 更换 → 解除
    me = next(c for c in snap["characters"] if c["id"] == snap["player_id"])
    child = next(c for c in snap["characters"] if c["father"] == me["id"] and not c["is_adult"] and c["alive"])
    guardian = next(c for c in snap["characters"]
                    if c["alive"] and c["is_adult"] and c["dynasty"] == me["dynasty"] and c["id"] != child["id"])
    r = client.post("/api/guardian", json={"child_id": child["id"], "guardian_id": guardian["id"]})
    assert r.json()["ok"], r.text
    snap = r.json()["state"]
    got = next(c for c in snap["characters"] if c["id"] == child["id"])
    assert got["guardian"] == guardian["id"]
    r = client.post("/api/guardian", json={"child_id": child["id"], "guardian_id": None})
    assert r.json()["ok"], r.text
    got = next(c for c in r.json()["state"]["characters"] if c["id"] == child["id"])
    assert got["guardian"] is None
    r = client.post("/api/guardian", json={"child_id": child["id"], "guardian_id": child["id"]})
    assert r.status_code == 400, "不能指定自己为监护人"
    print("[guardian api] OK  指定/解除/非法目标拒绝")

    # 改名：自己任意年龄；家主改宗族名
    r = client.post("/api/rename_self", json={"name": "新名测试"})
    assert r.json()["ok"], r.text
    assert r.json()["state"]["characters"][0]["name"] == "新名测试"
    r = client.post("/api/dynasty/rename", json={"name": "试验王朝"})
    assert r.json()["ok"], r.text
    assert any(d["name"] == "试验王朝" for d in r.json()["state"]["dynasties"])
    print("[rename api] OK  自己/宗族改名")

    # 关闭模组，回到原版世界
    r = client.post("/api/launcher/start", json={"enabled": []})
    assert r.json()["ok"], r.text

    # ── 调试杀人：默认关闭 ──
    r = client.post("/api/debug/kill", json={"target_id": 999})
    assert r.status_code == 403
    print("[debug kill off] OK  403 拒绝")

    # ── 自杀（正常模式可用）：家主身亡 → 继承/绝嗣流程 ──
    r = client.post("/api/suicide")
    res = r.json()
    assert res["ok"], res
    dead = next(c for c in res["state"]["characters"] if c["id"] == res["state"]["player_id"] or c["death_reason"] == "suicide")
    assert dead["death_reason"] == "suicide"
    assert res["state"]["over"] or any(e["type"] == "succession" for e in res["state"]["events"])
    if not res["state"]["over"]:
        assert res["state"]["death_notice"], "玩家死亡未生成通知"
        r = client.post("/api/notice/dismiss", json={"kind": "death"})
        assert r.json()["state"]["death_notice"] is None
        print("[death notice] OK  家主死亡通知已弹并确认清除")
    print("[suicide] OK  继承或绝嗣已触发")

    print("\nWebUI 冒烟测试全部通过 ✓")


if __name__ == "__main__":
    main()
