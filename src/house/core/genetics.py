"""遗传系统：属性遗传、先天特质继承、突变、近交、命名、教育授予。"""

from __future__ import annotations

import random
from typing import Optional

from .. import balance as B
from .. import i18n
from . import legacy
from . import traits as T
from .models import Character
from .world import World


def pick_name(world: World, culture: str, gender: str, *, exclude: set[str] | None = None) -> str:
    """从文化名字池抽取；exclude 提供的已用名（同宗同名序将追加罗马数字）。

    去重规则：推荐名避开同父/同母手足；手动输入不受约束（同名走「二世」）。
    """
    names = T.load_json("names.json").get("cultures", {}).get(culture, {})
    pool = names.get("male" if gender == "male" else "female", [])
    if exclude:
        free = [n for n in pool if n not in exclude]
        pool = free or pool  # 全被占用时回退全池（孩子将带同名序号）
    return world.rng.choice(pool) if pool else "无名"


def pick_dynasty_name(world: World, culture: str) -> str:
    names = T.load_json("names.json").get("cultures", {}).get(culture, {})
    pool = names.get("dynasties", [])
    return world.rng.choice(pool) if pool else "新家族"


def random_personality(world: World, count: int = 3) -> set[str]:
    chosen: set[str] = set()
    ids = list(T.PERSONALITY.keys())
    world.rng.shuffle(ids)
    for tid in ids:
        if len(chosen) >= count:
            break
        opp = set(T.PERSONALITY[tid].get("opposites", []))
        if opp & chosen:
            continue
        chosen.add(tid)
    return chosen


def _active_group_level(char: Character, group: str) -> Optional[int]:
    for tid, state in char.genes.items():
        if state == 2 and T.congenital_group(tid) == group:
            return T.congenital_level(tid)
    return None


def _set_group_trait(char: Character, group: str, level: int) -> None:
    # 清除同组其它等级，写入目标等级
    for tid in list(char.genes):
        if T.congenital_group(tid) == group:
            del char.genes[tid]
    if level == 0:
        return
    tid = f"{group}_{'n' if level < 0 else 'p'}{abs(level)}"
    if tid in T.TRAITS:
        char.genes[tid] = 2


def inherit_genes(world: World, father: Optional[Character], mother: Optional[Character]) -> dict[str, int]:
    genes: dict[str, int] = {}
    if father is None and mother is None:
        return genes
    all_ids = set()
    if father:
        all_ids |= set(father.genes)
    if mother:
        all_ids |= set(mother.genes)

    for tid in all_ids:
        fs = father.genes.get(tid, 0) if father else 0
        ms = mother.genes.get(tid, 0) if mother else 0
        p = B.CONGENITAL_INHERIT.get((fs, ms), 0.0)
        if world.rng.random() < p:
            genes[tid] = 2
        elif world.rng.random() < B.CONGENITAL_CARRIER_CHANCE:
            genes[tid] = 1

    # 双亲同组激活 -> 50% 升级
    groups = {T.congenital_group(t) for t in all_ids if T.congenital_group(t)}
    for group in groups:
        fl = _active_group_level(father, group) if father else None
        ml = _active_group_level(mother, group) if mother else None
        if fl is None or ml is None:
            continue
        if world.rng.random() < B.CONGENITAL_LEVELUP_CHANCE:
            sign = 1 if (fl + ml) >= 0 else -1
            new_level = min(3, max(abs(fl), abs(ml)) + 1) * sign
            _set_group_trait_from_genes(genes, group, new_level)

    # 突变：子代无任何激活先天特质时
    if not any(s == 2 for s in genes.values()) and world.rng.random() < B.CONGENITAL_MUTATION_CHANCE:
        positive = world.rng.random() < B.CONGENITAL_MUTATION_POSITIVE_RATIO
        pool = T.all_positive_congenital() if positive else T.all_negative_congenital()
        if pool:
            genes[world.rng.choice(pool)] = 2

    return genes


def _set_group_trait_from_genes(genes: dict[str, int], group: str, level: int) -> None:
    for tid in list(genes):
        if T.congenital_group(tid) == group:
            del genes[tid]
    tid = f"{group}_{'n' if level < 0 else 'p'}{abs(level)}"
    if tid in T.TRAITS:
        genes[tid] = 2


def roll_potential(world: World, father: Optional[Character], mother: Optional[Character]) -> dict[str, int]:
    """子代【基因基础属性】：向人群均值回归，只部分继承父母的基础值。

    这样可避免「教育/先天加成」代代叠加导致的数值膨胀（还原 CK3 的回归特性）。
    """
    potential: dict[str, int] = {}
    for key in B.ATTR_KEYS:
        bases = []
        if father:
            bases.append(father.potential.get(key, B.ATTR_BASE))
        if mother:
            bases.append(mother.potential.get(key, B.ATTR_BASE))
        if bases:
            parent_avg = sum(bases) / len(bases)
        else:
            parent_avg = B.ATTR_BASE
        val = B.ATTR_BASE + (parent_avg - B.ATTR_BASE) * B.ATTRIBUTE_INHERIT_RATIO
        val += world.rng.gauss(0, B.ATTRIBUTE_INHERIT_SIGMA)
        potential[key] = int(max(B.POTENTIAL_CLAMP[0], min(B.POTENTIAL_CLAMP[1], round(val))))
    return potential


def create_child(
    world: World,
    father_id: Optional[int],
    mother_id: Optional[int],
    patrilineal: bool = True,
) -> Character:
    father = world.get(father_id)
    mother = world.get(mother_id)

    if patrilineal and father is not None:
        dynasty = father.dynasty
        culture = world.dynasties[dynasty].culture if dynasty in world.dynasties else "czech"
    elif not patrilineal and mother is not None:
        dynasty = mother.dynasty
        culture = world.dynasties[dynasty].culture if dynasty in world.dynasties else "czech"
    else:
        parent = father or mother
        dynasty = parent.dynasty if parent else None
        culture = world.dynasties[dynasty].culture if dynasty in world.dynasties else "czech"

    gender = "male" if world.rng.random() < 0.5 else "female"

    # 同父/同母手足已用名 → 推荐名避开重名（同名者由世数后缀区分）
    used: set[str] = set()
    for pid in (father_id, mother_id):
        parent = world.get(pid)
        if parent is not None:
            for cid in parent.children:
                sib = world.get(cid)
                if sib is not None:
                    used.add(sib.name)

    genes = inherit_genes(world, father, mother)
    cong_attr = T.congenital_attr_bonus(genes)
    potential = roll_potential(world, father, mother)

    child = Character(
        id=world.new_char_id(),
        name=pick_name(world, culture, gender, exclude=used),
        gender=gender,
        birth_year=world.date.year,
        dynasty=dynasty,
        father=father_id,
        mother=mother_id,
        potential=potential,
        genes=genes,
        traits=random_personality(world),
    )
    # 新生儿属性 = 潜力的一小部分 + 先天加成 + 性格加成（CK3 采录值）
    cong = T.congenital_attr_bonus(genes)
    pers = T.personality_attrs(child.traits)
    for key in B.ATTR_KEYS:
        child.attributes[key] = max(0, round(potential[key] * 0.15) + cong.get(key, 0) + pers.get(key, 0))

    from .health import birth_health  # 延迟导入避免循环

    fm = legacy.family_modifiers(world, child.dynasty)
    child.health = birth_health(world, gender) + T.congenital_health_bonus(genes) + fm.get("health_add", 0.0)

    world.add_character(child)
    if father is not None:
        father.children.append(child.id)
        if father.spouse == mother_id:
            pass
    if mother is not None:
        mother.children.append(child.id)
    return child


TRAIT_PICK_AGES = (9, 12, 15)  # 性情抉择点位（CK3 童年多次性格事件，适配年龄）
GUARDIAN_TRAIT_INFLUENCE = 0.6  # 候选之一跟随监护人性格的概率（适配，可调）


def grow_children(world: World) -> None:
    """每年推进一次：童年特质显现、性情抉择、教育判定（CK3）、属性成长、16 岁定型。"""
    for child in world.alive():
        age = child.age
        if age >= B.CHILDHOOD_END:
            if child.education is None:
                finalize_education(world, child)
            continue
        if age < B.CHILDHOOD_START:
            continue
        # ── 6 岁生日：童年特质显现 + 进入教养队列 ──
        if child.childhood_trait is None:
            T.roll_childhood_trait(world, child)
            child.education_focus = T.childhood_focus(child.childhood_trait)  # CK3 默认推定
            params = {"child": child.name, "trait": T.childhood_name(child.childhood_trait)}
            world.add_log(f"🧒 {i18n.t('event.childhood_trait', **params)}")
            world.add_event("trait", "event.childhood_trait", params, [child.id])
            if world.is_descendant(child.id, world.player_id):
                world.tutoring_queue.append({"child_id": child.id})
            else:
                auto_tutor(world, child)
        elif child.education_focus is None:
            child.education_focus = T.childhood_focus(child.childhood_trait)
        # ── 9/12/15 岁：性情抉择（CK3 童年多次性格事件，适配点位） ──
        if age in TRAIT_PICK_AGES and not any(e.get("child_id") == child.id for e in world.trait_queue):
            if world.is_descendant(child.id, world.player_id):
                world.trait_queue.append({"child_id": child.id, "age": age})
            else:
                _auto_trait_pick(world, child)
        # ── 年度教育判定（CK3 生日 roll：成功 +2 分） ──
        if child.education_focus is not None and child.education is None:
            if world.rng.random() < _edu_success_chance(world, child):
                child.education_score += B.EDU_SCORE_PER_SUCCESS
        # ── 属性向潜力成长（原有成长曲线保留） ──
        cong = T.congenital_attr_bonus(child.genes)
        progress = (age - B.CHILDHOOD_START + 1) / (B.CHILDHOOD_END - B.CHILDHOOD_START)
        for key in B.ATTR_KEYS:
            goal = child.potential[key] + cong.get(key, 0)
            target = round(goal * (0.3 + 0.7 * progress))
            cur = child.attributes[key]
            child.attributes[key] = cur + max(1, round((target - cur) * 0.34))


def trait_pick_options(
    world: World, child: Character, rng: Optional[random.Random] = None
) -> tuple[str, str]:
    """性情抉择的两个候选特质 id：(师长言传, 率性而为)。

    师长言传：监护人自己的性格（监护缺位则随机）；率性而为：随机、优先与既有特质成对。
    rng 可传入独立随机源（presenter 展示用），缺省用游戏 rng（AI 决策）。
    """
    roll = rng or world.rng
    personality_ids = list(T.PERSONALITY_IDS)
    if not personality_ids:
        return "", ""
    own = set(child.traits)

    def _pick(pool: list[str]) -> str:
        free = [p for p in pool if p not in own]
        return roll.choice(free) if free else roll.choice(pool)

    guardian = world.get(child.guardian)
    if guardian is not None and guardian.traits and roll.random() < GUARDIAN_TRAIT_INFLUENCE:
        taught = _pick(sorted(guardian.traits))
    else:
        taught = _pick(personality_ids)
    # 率性而为：优先与自身既有特质相反的特质（CK3 性格成对结构）
    opposite_pool = [
        p for p in personality_ids
        if any(p in T.PERSONALITY.get(o, {}).get("opposites", []) for o in own)
    ]
    stray = _pick(opposite_pool or personality_ids)
    if stray == taught:
        stray = _pick([p for p in personality_ids if p != taught])
    return taught, stray


def apply_trait_pick(world: World, child: Character, trait_id: str) -> None:
    """应用性情抉择结果；改特质会给监护人/家长留下压力（API 存根）。"""
    from . import stress

    child.traits = set(child.traits) | {trait_id}
    params = {"child": child.name, "trait": T.trait_name(trait_id)}
    world.add_log(f"🌿 {i18n.t('event.trait_gain', **params)}")
    world.add_event("trait", "event.trait_gain", params, [child.id])
    # 压力钩子（未实现的状态层；落地时 Character.stress 由该入口累积）
    stress.add_stress(world, child.guardian, 20, "stress.reason.ward_trait")


def _auto_trait_pick(world: World, child: Character) -> None:
    """AI 孩童的自动抉择：偏监护人侧（师长的天性）。"""
    taught, stray = trait_pick_options(world, child)
    apply_trait_pick(world, child, taught if world.rng.random() < 0.7 else stray)
    world.trait_queue = [e for e in world.trait_queue if e.get("child_id") != child.id]


def _child_edu_success_factor(world: World, child: Character) -> int:
    factor = 0
    for tid, state in child.genes.items():
        if state == 2 and T.congenital_group(tid) == "intellect":
            factor += B.EDU_CHILD_INTELLECT_FACTOR.get(str(T.congenital_level(tid)), 0)
    if child.childhood_trait is not None and child.education_focus is not None:
        factor += (
            B.EDU_CHILDHOOD_MATCH
            if T.childhood_focus(child.childhood_trait) == child.education_focus
            else -B.EDU_CHILDHOOD_MATCH
        )
    return factor


def _guardian_edu_factors(world: World, child: Character) -> tuple[int, int]:
    """(成功因子, 失败因子) 中监护人部分。"""
    guardian = world.get(child.guardian)
    if guardian is None or not guardian.is_alive:
        return 0, B.EDU_NO_GUARDIAN_FAIL
    success, failure = 0, 0
    for tid, state in guardian.genes.items():
        if state == 2 and T.congenital_group(tid) == "intellect":
            lvl = T.congenital_level(tid)
            if lvl > 0:
                success += B.EDU_GUARDIAN_INTELLECT_FACTOR.get(str(lvl), 0)
    if guardian.attributes:
        success += int(round(B.EDU_GUARDIAN_SKILL_WEIGHT * guardian.attributes.get(child.education_focus, 0)))
        success += int(round(B.EDU_GUARDIAN_LEARNING_WEIGHT * guardian.attributes.get("learning", 0)))
    return success, failure


def _child_edu_failure_factor(world: World, child: Character) -> int:
    factor = 0
    for tid, state in child.genes.items():
        if state == 2 and T.congenital_group(tid) == "intellect":
            lvl = T.congenital_level(tid)
            if lvl < 0:
                factor += B.EDU_CHILD_INTELLECT_FACTOR.get(str(lvl), 0)
        if state == 2 and tid == "inbred":
            factor += T.TRAITS.get("inbred", {}).get("edu_penalty", 20)
    return factor


def _edu_success_chance(world: World, child: Character) -> float:
    """CK3 教育判定：成功率 = (60 + 成功因子) / (100 + 成功因子 + 失败因子)。"""
    child_factor = _child_edu_success_factor(world, child)
    guardian_success, guardian_failure = _guardian_edu_factors(world, child)
    success_factor = child_factor + guardian_success
    failure_factor = _child_edu_failure_factor(world, child) + guardian_failure
    p = (B.EDU_SUCCESS_FACTOR_BASE + success_factor) / (
        B.EDU_SCORE_DIVISOR_BASE + success_factor + failure_factor
    )
    return max(0.0, min(1.0, p))


def auto_tutor(world: World, child: Character) -> None:
    """AI 家族孩子的自动教养：焦点=童年特质推定，监护人=同族最高相关技能成人。"""
    if child.education_focus is None and child.childhood_trait is not None:
        child.education_focus = T.childhood_focus(child.childhood_trait)
    if child.guardian is None:
        dyn = child.dynasty
        focus = child.education_focus or "diplomacy"
        best, best_val = None, -1
        for c in world.alive():
            if c.id == child.id or c.dynasty != dyn or not c.is_adult:
                continue
            val = c.attributes.get(focus, 0) + c.attributes.get("learning", 0)
            if val > best_val:
                best, best_val = c, val
        if best is not None:
            child.guardian = best.id


def finalize_education(world: World, child: Character) -> None:
    score = child.education_score
    level = 1
    for threshold, lv in B.EDU_SCORE_TIERS:  # [(18,4),(13,3),(8,2),(0,1)]
        if score >= threshold:
            level = lv
            break
    route = child.education_focus or max(
        B.ATTR_KEYS[:-1], key=lambda k: child.potential.get(k, 0)
    )  # 兜底：按潜力选择（不含勇武）
    child.education = f"edu_{route}_{level}"
    world.tutoring_queue = [e for e in world.tutoring_queue if e.get("child_id") != child.id]
    world.trait_queue = [e for e in world.trait_queue if e.get("child_id") != child.id]
    # ── 童年特质成年转换（CK3：childhood → personality） ──
    converted_note = ""
    if child.childhood_trait:
        adult_trait = T.childhood_conversion(child.childhood_trait)
        if adult_trait and adult_trait in T.PERSONALITY and adult_trait not in child.traits:
            child.traits = set(child.traits) | {adult_trait}
            converted_note = f"，童年的「{T.childhood_name(child.childhood_trait)}」化作「{T.trait_name(adult_trait)}」"
    cong = T.congenital_attr_bonus(child.genes)
    edu = T.education_attr_bonus(child.education)
    pers = T.personality_attrs(child.traits)
    for key in B.ATTR_KEYS:
        val = child.potential[key] + cong.get(key, 0) + edu.get(key, 0) + pers.get(key, 0)
        child.attributes[key] = max(B.ATTR_MIN, min(B.ATTR_MAX, val))
    world.add_log(
        f"🌱 {i18n.t('event.adulthood', child=child.name, education=T.education_name(child.education), score=score)}"
        f"{converted_note}"
    )
    world.add_event(
        "adulthood", "event.adulthood",
        {"child": child.name, "education": T.education_name(child.education), "score": score},
        [child.id],
    )

