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

    # ── 推旬 ──
    before = snap["date"]
    r = client.post("/api/tick", json={"unit": "xun"})
    assert r.status_code == 200
    snap = r.json()["state"]
    assert (snap["date"]["year"], snap["date"]["month"], snap["date"]["xun"]) != (
        before["year"], before["month"], before["xun"]
    )
    print("[tick xun] OK")

    # ── 推年（stop_on_naming：可能停在起名事件）──
    r = client.post("/api/tick", json={"unit": "year"})
    snap = r.json()["state"]
    advanced = snap["date"]["year"] - before["year"]
    assert snap["naming_queue"] or snap["over"] or advanced >= 1, f"推年异常：{snap['date']}"
    print("[tick year] OK  推进到", snap["date"]["label"])

    # ── 起名（构造一个确定待命名场景：直接推年直到队列非空）──
    for _ in range(30):
        snap = client.post("/api/tick", json={"unit": "year"}).json()["state"]
        if snap["over"] or snap["naming_queue"]:
            break
    if snap["naming_queue"]:
        entry = snap["naming_queue"][0]
        r = client.post("/api/naming", json={"child_id": entry["child_id"], "name": "测试之子"})
        assert r.status_code == 200
        res = r.json()
        assert res["ok"] and all(e["child_id"] != entry["child_id"] for e in res["state"]["naming_queue"])
        child = next(c for c in res["state"]["characters"] if c["id"] == entry["child_id"])
        assert child["name"] == "测试之子"
        print("[naming] OK  命名", entry["suggested"], "-> 测试之子")
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
    for _ in range(12):
        snap = client.post("/api/tick", json={"unit": "year"}).json()["state"]
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
    if own and other:
        a, b = own[0], other[0]
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
        print("[betrothal] SKIP  无可订孩子")

    # ── 性情抉择（9/12/15 岁） + 童年特质/转换存在性 ──
    snap = client.get("/api/state").json()
    kids = [c for c in snap["characters"] if c["alive"] and not c["is_adult"]]
    if not snap["trait_queue"] and kids:
        # 快进到第一个抉择点
        for _ in range(12):
            s2 = client.post("/api/tick", json={"unit": "year"}).json()["state"]
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
        for _ in range(8):
            s2 = client.post("/api/tick", json={"unit": "year"}).json()["state"]
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
    print("[suicide] OK  继承或绝嗣已触发")

    print("\nWebUI 冒烟测试全部通过 ✓")


if __name__ == "__main__":
    main()
