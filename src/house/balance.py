"""集中式数值定义 —— 唯一的数值来源。

所有游戏平衡数值都放这里，禁止在其它模块里写魔法数字。
数值锚定 CK3 官方 wiki；修改后请跑 tools/sim_balance.py 校准。
"""

from __future__ import annotations

# ── 时间（现代公历，一日一回合） ─────────────────────────
START_YEAR = 1066
MONTHS_PER_YEAR = 12
DAYS_PER_MONTH_NORMAL = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
DAYS_PER_MONTH_LEAP = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
PREGNANCY_DAYS = 273                       # 妊娠约 9 个公历月（9 * 30.4 ≈ 273）
EVENT_DUE_DAYS = 60                        # 待人事件（命名/教养/择性）逾期自动落定：两个月按 60 天

# ── 属性 ────────────────────────────────────────────────
ATTRS: dict[str, str] = {
    "diplomacy": "外交",
    "martial": "军事",
    "stewardship": "管理",
    "intrigue": "谋略",
    "learning": "学识",
    "prowess": "勇武",
}
ATTR_KEYS: list[str] = list(ATTRS)
ATTR_BASE = 8
ATTR_MIN = 0
ATTR_MAX = 100

# ── 生育（公式与数值锚定 CK3 wiki 1.20） ─────────────────
FERTILITY_BASE = 50.0                      # 基础生育力 %
FERTILITY_CHANCE_MULTIPLIER = 4.75         # 月受孕率 = 双亲有效生育力均值 * 4.75 / 100
FERTILITY_AGE_MALE: list[tuple[int, int, float]] = [
    (16, 35, 1.0), (36, 40, 0.9), (41, 45, 0.8),
    (46, 50, 0.8), (51, 60, 0.7), (61, 70, 0.6), (71, 999, 0.5),
]
FERTILITY_AGE_FEMALE: list[tuple[int, int, float]] = [
    (16, 25, 1.0), (26, 30, 0.9), (31, 35, 0.7),
    (36, 40, 0.5), (41, 45, 0.33), (46, 999, 0.0),
]
FERTILITY_DECAY_OFFSET_FECUND = 5          # 多产 / 康强的身体：衰减起点 +5 岁
FERTILITY_NON_RULER_PENALTY = 15.0         # 双方均非统治者时，生育力 -15
FERTILITY_LOVER_BONUS = 25.0               # 情人 / 灵魂伴侣 +25 生育力
FERTILITY_CONCUBINE_MULTIPLIER = 0.5       # 妾 / 次妻生育力减半
FERTILITY_PER_CHILD_PENALTY = 5.0          # 母亲每生育一胎 -5 生育力
MAX_CHILDREN_FEMALE = 9                    # 女性最多 9 胎（第 9 胎双胞胎除外）
MAX_CHILDREN_MALE_BASE = 9                 # 男性最多 9 个存活子女
MALE_CHILDREN_PER_EXTRA_CONSORT = 2        # 每额外配偶 +2 男性上限
TWIN_CHANCE = 0.03                         # 双胞胎 3%（游戏数据值，wiki 无表）
# 分娩死亡：基础 + 年龄项；wiki 定性「母亲健康越低越危险、经产顾客更安全」→ 档位乘数（可调）
CHILDBED_DEATH_BASE = 0.015                # 分娩死亡基础风险（随年龄上升）
CHILDBED_DEATH_AGE_FACTOR = 0.0015
CHILDBED_HEALTH_MULT: list[tuple[float, float]] = [
    (7.0, 0.8), (5.0, 1.0), (3.0, 1.5), (1.0, 3.0), (float("-inf"), 8.0),
]   # (健康下界, 乘数)，取第一条满足的档位
CHILDBED_EXP_MULT: list[tuple[int, float]] = [
    (4, 0.5), (3, 0.6), (2, 0.75), (0, 1.0),
]   # (已产数下界, 乘数)

# ── 宝物（CK3 Artifacts：稀有度决定耐久/维修/销毁返金） ──
ARTIFACT_SLOTS = ("weapon", "armor", "regalia", "trinket")
ARTIFACT_RARITIES: dict[str, dict] = {
    "common": {"durability": 60, "destroy_gold": 40, "reforge_cost": 65},
    "masterwork": {"durability": 75, "destroy_gold": 80, "reforge_cost": 125},
    "famed": {"durability": 100, "destroy_gold": 150, "reforge_cost": 250},
    "illustrious": {"durability": 150, "destroy_gold": 250, "reforge_cost": 625},
}
ARTIFACT_DURABILITY_YEARLY = 1            # CK3：每件宝物每年损失 1 点耐久
ARTIFACT_INHERIT_STRANGER_LOSS = 10       # 非近亲继承时的额外耐久损失（CK3）

# ── 压力（CK3 1.20 wiki：0-400；100/200/300 三档；400 强制崩溃） ──
STRESS_MAX = 400
STRESS_TIER_THRESHOLDS = (100, 200, 300)
STRESS_FERTILITY_MULT = {0: 1.0, 1: 0.9, 2: 0.7, 3: 0.5}      # 每档生育力乘数（−10%/−30%/−50%）
STRESS_HEALTH_PENALTY = {0: 0.0, 1: 0.0, 2: -1.0, 3: -2.0}     # 每档健康惩罚
STRESS_BREAK_COOLDOWN_DAYS = 5 * 365                            # 精神崩溃 5 年一次（wiki）
STRESS_BREAK_LOSS = 60                                          # 崩溃选特质时的减压量（wiki 未给精确值，采定）
STRESS_ENDURE_GAIN = 20                                         # 硬撑：再涨压力
MAX_COPING_TRAITS = 2                                           # 应对机制最多 2 个（wiki）
STRESS_GAIN_MINOR = 20                                          # CK3 script value minor_stress_gain（wiki 原文）
STRESS_GAIN_MEDIUM = 30                                         # 采定（wiki 未列数值）
# 血亲死亡：配偶/子女/父母=30，兄弟姐妹=20，祖孙=15（CK3 on_death 分级采定）
GRIEF_STRESS_SPOUSE_CHILD_PARENT = 30
GRIEF_STRESS_SIBLING = 20
GRIEF_STRESS_GRANDPARENT = 15

# ── 健康 ────────────────────────────────────────────────
BIRTH_HEALTH_MALE = (4.5, 4.9)
BIRTH_HEALTH_FEMALE = (5.0, 5.4)
HEALTH_LOSS_START_AGE = 25
HEALTH_LOSS_CHANCE = 0.075
HEALTH_LOSS_CHANCE_INCREMENT = 0.022
HEALTH_LOSS_AMOUNT = 0.125
PROWESS_LOSS_START_AGE = 45
PROWESS_LOSS_CHANCE = 0.10
PROWESS_LOSS_CHANCE_INCREMENT = 0.015
OLD_AGE_DEATH_AGE = 60
DISEASE_YEARLY_CHANCE = 0.10
DISEASE_HEALTH_LOSS = 0.5
# 健康档位：(下界, 名称)，上界取下一条下界
HEALTH_TIERS: list[tuple[float, str]] = [
    (float("-inf"), "濒死"), (0.0, "垂危"), (1.0, "差"),
    (3.0, "尚可"), (5.0, "好"), (7.0, "极佳"),
]

# ── 遗传（锚定 CK3） ────────────────────────────────────
# (父状态, 母状态) -> 子代激活概率；状态：0 无 / 1 隐性 / 2 显性
CONGENITAL_INHERIT: dict[tuple[int, int], float] = {
    (0, 0): 0.0,
    (0, 1): 0.02, (0, 2): 0.25,
    (1, 1): 0.10, (1, 2): 0.50,
    (2, 2): 0.80,
}
CONGENITAL_MUTATION_CHANCE = 0.127         # 双亲皆无时，子代突变概率
CONGENITAL_MUTATION_POSITIVE_RATIO = 0.20  # 突变中正面特质占比（约 2.6/12.7）
CONGENITAL_CARRIER_CHANCE = 0.15           # 未激活时成为隐性携带者的概率（隔代遗传）
CONGENITAL_LEVELUP_CHANCE = 0.50           # 双亲同组激活 -> 子代升级概率
INBREEDING_FACTOR = 0.30                   # 近交系数 = 亲缘系数 * 0.30
ATTRIBUTE_INHERIT_RATIO = 0.30             # 子代基础属性向父母均值靠拢的比例（其余回归人群均值）
ATTRIBUTE_INHERIT_SIGMA = 2.5              # 属性遗传的正态扰动
CHILDHOOD_START = 6
CHILDHOOD_END = 16
CHILDHOOD_PARENT_GAIN = 4                  # 6-16 岁可从父母处获得的属性上限
POTENTIAL_CLAMP = (0, 40)

# ── 教育（CK3 判定公式，wiki 1.20 原始数值） ─────────────
EDU_SCORE_PER_SUCCESS = 2                  # 每次成功 +2 分（10 次生日判定）
EDU_SUCCESS_FACTOR_BASE = 60.0             # 成功率 = (60+成功因子)/(100+成功因子+失败因子)
EDU_SCORE_DIVISOR_BASE = 100.0
# 得分 -> 教育特质等级
EDU_SCORE_TIERS: list[tuple[int, int]] = [
    (18, 4), (13, 3), (8, 2), (0, 1),
]
# 得分因子：孩子智力组（按等级）、童年特质匹配、监护人技能、监护人智力组
EDU_CHILD_INTELLECT_FACTOR = {"3": 20, "2": 15, "1": 10, "-1": 10, "-2": 15, "-3": 20}
EDU_GUARDIAN_INTELLECT_FACTOR = {"3": 15, "2": 10, "1": 5}
EDU_CHILDHOOD_MATCH = 20                   # 童年特质与教育方向匹配（不匹配 -20）
EDU_GUARDIAN_SKILL_WEIGHT = 0.4            # 监护人相关技能
EDU_GUARDIAN_LEARNING_WEIGHT = 0.2         # 监护人学识
EDU_NO_GUARDIAN_FAIL = 20                  # 无监护人：失败因子 +20
# CK3 教育特质属性加成：1/2/3/4 级 = +2/+5/+8/+10（ traits.json 同步）

# ── 婚姻 ────────────────────────────────────────────────
CONSORT_LIMIT = 1                          # 眷属上限（配偶数；未来可含妾/次妻）
# 性取向分布（CK3 不影响生育；默认分布无官方表，中置信度可调）
SEXUALITY_WEIGHTS: list[tuple[str, float]] = [
    ("heterosexual", 0.88), ("homosexual", 0.06), ("bisexual", 0.05), ("asexual", 0.01),
]
# AI 自动婚配意愿乘数（适配：CK3 中同/无性恋 AI 结婚意愿更低）
SEXUALITY_AI_MARRIAGE_MULT: dict[str, float] = {
    "heterosexual": 1.0, "bisexual": 1.0, "homosexual": 0.35, "asexual": 0.35,
}

# ── 资源（占位锚点，M3+ 细化） ───────────────────────────
PRESTIGE_YEARLY_BASE = 12.0
PIETY_YEARLY_BASE = 6.0
RENOWN_YEARLY_BASE = 2.0
MONEY_YEARLY_BASE = 24.0

# ── 世界规模（防止封闭世界人口指数爆炸的游戏抽象） ────────
WORLD_SOFT_CAP = 90         # 存活角色软上限：接近后节流 NPC 婚配与非玩家生育
WORLD_HARD_CAP = 160        # 硬上限：达到后自动婚配停止、非玩家受孕大幅下降
CHILD_MORTALITY_YEARLY = 0.010   # 儿童年度早夭概率（近似，含意外/疾病）
ADULT_ACCIDENT_YEARLY = 0.004    # 成年人年度意外死亡概率（近似）
