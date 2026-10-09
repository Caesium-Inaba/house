"""压力系统存根（CK3 Stress 0-400；本批仅留 API，不落地状态）。

后续落地时：Character 增 stress 字段逐档生效（≥100 精神崩溃 PICK 应对特质、
-10%/-30%/-50% 生育力、健康 -1/-2），见 CK3 wiki Attributes#Stress。
"""

from __future__ import annotations

from .world import World


def add_stress(world: World, char_id: int | None, amount: int, reason: str = "") -> None:
    """统一压力入口：当前为 no-op 存根。

    - reason 用 i18n key（如 stress.reason.forced_trait），便于将来粒度翻译。
    - 落地时在此维护 Character.stress 并触发崩溃判定；接口签名不变。
    """
    return None
