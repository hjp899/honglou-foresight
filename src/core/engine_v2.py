#!/usr/bin/env python3
"""
红楼梦伏笔约束推理引擎 v2.0
==============================
升级功能：
1. 加权约束传播 — 基于来源权威性(scholar_credibility.json)自动加权
2. 曹雪芹风格检验 — 加载caoxueqin_profile.json，自动评估新假说是否符合作者逻辑
3. 实时重载 — 社区更新数据文件后引擎自动重新加权
4. 多假设并行对比 — 同时评估多个替代结局方案的一致性得分

继承 v1.0 的所有功能（约束传播、拓扑排序、一致性检查）。
"""

import json
import os
import time
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum


# ============================================================
# 来源权威性
# ============================================================

class AuthorityLevel(Enum):
    ORIGINAL_TEXT = 100        # 前80回原文
    ZHUPI_CERTAIN = 95        # 脂批确定性
    JIHU = 85                  # 畸笏叟批
    ZHUPI_HINT = 70           # 脂批暗示性
    SCHOLAR_CONSENSUS = 75    # 红学大家学术共识
    SCHOLAR_INDIVIDUAL = 55   # 红学大家个人观点
    PROFESSOR = 40             # 顶级文学教授研究
    AMATEUR = 10               # 网络/自媒体观点


class ScholarCredibility:
    """学者权威性评级系统"""

    def __init__(self, data_dir: str):
        self.profiles = {}
        self.source_weights = {}
        self.disputed_topics = {}
        self._load(data_dir)

    def _load(self, data_dir: str):
        try:
            path = os.path.join(data_dir, 'scholar_credibility.json')
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.source_weights = data.get('source_weights', {})
            self.disputed_topics = data.get('disputed_topics', {})

            for p in data.get('scholar_profiles', []):
                self.profiles[p['name']] = {
                    'authority_level': p['authority_level'],
                    'weight_multiplier': p.get('weight_multiplier', 0.5),
                    'credibility_note': p.get('credibility_note', ''),
                    'controversial_views': p.get('controversial_views', []),
                }
        except FileNotFoundError:
            pass

    def get_weight(self, source_type: str, scholar_name: str = None) -> float:
        """获取某个来源的权威性权重 (0-100)"""
        # Map evidence types to source weight categories
        type_map = {
            '前80回文本伏笔': '前80回原文',
            '脂批直接提示': '脂砚斋批语_确定性',
            '判词/谶语': '前80回原文',
            '人物性格逻辑': '前80回原文',
        }
        mapped = type_map.get(source_type, source_type)

        for key, info in self.source_weights.items():
            if key == mapped:
                base = info.get('weight', 50)
                if scholar_name and scholar_name in self.profiles:
                    base *= self.profiles[scholar_name]['weight_multiplier']
                return base

        return 30  # default low weight for unknown sources

    def is_controversial(self, scholar_name: str, topic: str) -> bool:
        """检查某学者在某话题上是否有争议观点"""
        if scholar_name in self.profiles:
            for view in self.profiles[scholar_name].get('controversial_views', []):
                if topic in view:
                    return True
        return False


# ============================================================
# 曹雪芹模型
# ============================================================

class CaoXueqinModel:
    """
    曹雪芹风格模型 — 用于评估新假说是否符合曹氏文学逻辑。

    加载 caoxueqin_profile.json，对输入的结局假说进行三维评估：
    1. 哲学立场 — 是否符合'真假有无'的辩证、'假作真时真亦假'的世界观
    2. 叙事逻辑 — 是否符合人物性格逻辑的必然发展、是否存在伏笔呼应
    3. 写作模式 — 是否符合曹氏的可辨识行文模式（盛极必衰、小人物逆转、悲喜交加）
    """

    def __init__(self, data_dir: str):
        self.profile = {}
        self.rigid_rules = []
        self.strong_rules = []
        self.speculative_rules = []
        self.style_dimensions = {}
        self.patterns = []
        self.techniques = []
        self._load(data_dir)

    def _load(self, data_dir: str):
        try:
            path = os.path.join(data_dir, 'caoxueqin_profile.json')
            with open(path, 'r', encoding='utf-8') as f:
                self.profile = json.load(f)

            author_model = self.profile.get('author_model', {})
            self.rigid_rules = author_model.get('level_1_rigid', {}).get('rules', [])
            self.strong_rules = author_model.get('level_2_strong', {}).get('rules', [])
            self.speculative_rules = author_model.get('level_3_speculative', {}).get('rules', [])
            self.style_dimensions = self.profile.get('style_evaluator', {}).get('dimensions', {})
            self.patterns = self.profile.get('cao_xueqin_patterns', {}).get('patterns', [])
            self.techniques = self.profile.get('writing_techniques', {}).get('techniques', [])
        except FileNotFoundError:
            pass

    def evaluate_hypothesis(self, hypothesis: str, supporting_evidence: List[str] = None) -> Dict[str, Any]:
        """
        评估一个结局假说是否符合曹雪芹的逻辑。

        返回: {
            'cao_score': 0-100 的符合度评分,
            'violations': 违反的刚性/强约束列表,
            'alignments': 符合的约束列表,
            'style_notes': 风格层面评价
        }
        """
        violations = []
        alignments = []
        style_notes = []

        # Check rigid rules
        for rule in self.rigid_rules:
            if self._violates(rule, hypothesis):
                violations.append({'level': 'rigid', 'rule': rule})
            else:
                # Simple heuristic: if hypothesis mentions the same topic
                topic_words = rule[:10]
                if any(w in hypothesis for w in ['悲剧', '出家', '泪尽', '自杀自灭', '赐死']):
                    if self._aligns(rule, hypothesis):
                        alignments.append({'level': 'rigid', 'rule': rule})

        # Check strong rules
        for rule in self.strong_rules:
            if self._violates(rule, hypothesis):
                violations.append({'level': 'strong', 'rule': rule})

        # Calculate score
        rigid_penalty = len([v for v in violations if v['level'] == 'rigid']) * 30
        strong_penalty = len([v for v in violations if v['level'] == 'strong']) * 15
        base_score = 100
        cao_score = max(0, base_score - rigid_penalty - strong_penalty)

        # Add style evaluation
        for dim_name, dim_info in self.style_dimensions.items():
            anti_patterns = dim_info.get('anti_patterns', [])
            for ap in anti_patterns:
                if any(keyword in hypothesis for keyword in ['好人', '坏人', '报应', '复仇', '皆大欢喜', '团圆', '绝望', '虚无']):
                    if self._matches_anti_pattern(ap, hypothesis):
                        style_notes.append({
                            'dimension': dim_name,
                            'issue': ap,
                            'severity': 'warning'
                        })
                        cao_score = max(0, cao_score - 5)

        return {
            'cao_score': cao_score,
            'violations': violations,
            'alignments': alignments,
            'style_notes': style_notes,
            'verdict': '通过' if cao_score >= 70 else ('存疑' if cao_score >= 40 else '否决'),
        }

    def _violates(self, rule: str, hypothesis: str) -> bool:
        """Detect if hypothesis contradicts a rule using keyword matching.
        Rule-specific character names must also appear in the hypothesis for a match."""
        # Each rule maps to (required_context_keywords, contradicting_keywords)
        rule_patterns = {
            '全书以绝对悲剧收场': (None, ['团圆', '幸福结局', '皆大欢喜', '复荣', '兰桂齐芳']),
            '宝玉最终出家': (['宝玉'], ['还俗', '还家', '中举', '做官', '陪伴宝钗到老']),
            '黛玉之死不是焚稿断情': (None, ['焚', '含恨', '泄愤', '报复宝玉', '调包计']),
            '元春之死是政治赐死': (['元春'], ['病逝', '善终', '寿终正寝']),
            '鸳鸯在贾母死后必然遭到贾赦报复': (['鸳鸯'], ['善终', '幸福', '自由']),
            '秦可卿原稿为淫丧天香楼': (['秦可卿','可卿'], ['病死', '自然死亡']),
        }
        for rule_key, (ctx_words, contra_words) in rule_patterns.items():
            if rule_key in rule:
                # Check context: if ctx_words specified, at least one must appear in hypothesis
                if ctx_words and not any(w in hypothesis for w in ctx_words):
                    continue  # Rule doesn't apply to this character
                for w in contra_words:
                    if w in hypothesis:
                        return True
        return False

    def _aligns(self, rule: str, hypothesis: str) -> bool:
        """Simple positive alignment check"""
        return any(w in hypothesis for w in rule[:10])

    def _matches_anti_pattern(self, pattern: str, hypothesis: str) -> bool:
        keywords = {
            '非黑即白的道德判断': ['好人', '坏人', '善有善报', '恶有恶报'],
            '纯粹喜庆的结局': ['幸福', '圆满', '团聚', '皆大欢喜'],
            '完全绝望的虚无主义': ['全灭', '死绝', '无一幸免', '彻底毁灭'],
        }
        for kw in keywords.get(pattern[:6], []):
            if kw in hypothesis:
                return True
        return False

    def reload(self, data_dir: str):
        """社区更新数据文件后重新加载模型"""
        self._load(data_dir)


# ============================================================
# 加权约束图
# ============================================================

class WeightedConstraint:
    __slots__ = ('id', 'type', 'source', 'target', 'rationale',
                 'strength', 'source_weight', 'scholar_weight')
    def __init__(self, cst_id, cst_type, source, target,
                 rationale, strength, source_weight=50, scholar_weight=1.0):
        self.id = cst_id
        self.type = cst_type
        self.source = source
        self.target = target
        self.rationale = rationale
        self.strength = strength
        self.source_weight = source_weight
        self.scholar_weight = scholar_weight

    @property
    def effective_weight(self) -> float:
        return self.source_weight * self.scholar_weight


class WeightedConstraintGraph:
    """带权重的约束图——支持自动加权和衰减"""

    def __init__(self, scholar_cred: ScholarCredibility):
        self.graph: Dict[str, List[Tuple[str, str, str, float]]] = defaultdict(list)
        self.reverse_graph: Dict[str, List[Tuple[str, str, str, float]]] = defaultdict(list)
        self.constraints: Dict[str, WeightedConstraint] = {}
        self.scholar = scholar_cred

    def add_constraint(self, cst, evidence_type: str = '前80回文本伏笔',
                       scholar: str = None):
        source_weight = self.scholar.get_weight(evidence_type, scholar)
        scholar_w = self.scholar.profiles.get(scholar, {}).get('weight_multiplier', 1.0)

        wc = WeightedConstraint(
            cst_id=cst.id,
            cst_type=cst.type,
            source=cst.source,
            target=cst.target,
            rationale=cst.rationale,
            strength=cst.strength,
            source_weight=source_weight,
            scholar_weight=scholar_w,
        )
        self.constraints[cst.id] = wc

        eff = wc.effective_weight
        self.graph[cst.source].append((cst.target, cst.type, cst.strength, eff))
        self.reverse_graph[cst.target].append((cst.source, cst.type, cst.strength, eff))

    def get_weighted_consequences(self, node: str, max_depth: int = 5) -> Dict[str, List[Tuple[str, float]]]:
        """返回带权重的传播结果"""
        visited = {node}
        queue = deque([(node, 0, 100.0)])
        results: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

        while queue:
            current, depth, parent_weight = queue.popleft()
            if depth >= max_depth:
                continue
            for target, ctype, strength, edge_weight in self.graph.get(current, []):
                propagated_weight = min(parent_weight, edge_weight)
                results[ctype].append((target, propagated_weight))
                if target not in visited:
                    visited.add(target)
                    queue.append((target, depth + 1, propagated_weight))
        return dict(results)

    def rank_supporting(self, node: str) -> List[Tuple[str, str, float]]:
        """返回支持某个节点的证据，按权重降序排序"""
        evidence = self.reverse_graph.get(node, [])
        return sorted(evidence, key=lambda x: x[3], reverse=True)


# ============================================================
# 多假设对比器
# ============================================================

class HypothesisComparator:
    """
    同时评估多个替代结局方案，按'曹雪芹符合度得分'排名。
    """

    def __init__(self, cao_model: CaoXueqinModel,
                 cg: WeightedConstraintGraph,
                 characters: Dict[str, Any],
                 foreshadowings: Dict[str, Any]):
        self.cao_model = cao_model
        self.cg = cg
        self.characters = characters
        self.foreshadowings = foreshadowings

    def compare(self, hypotheses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        输入多个假设方案，返回排序后的对比结果。

        每个 hypothesis: {
            'label': '黛玉病逝说',
            'description': '...',
            'character_id': 'CHAR-02',
            'related_foreshadowings': ['FS-002', 'FS-003', ...]
        }
        """
        results = []
        for hyp in hypotheses:
            # 1. 曹雪芹风格检验
            cao_eval = self.cao_model.evaluate_hypothesis(
                hyp['description'],
                supporting_evidence=hyp.get('related_foreshadowings', [])
            )

            # 2. 约束图传播支持度
            total_weight = 0
            rigid_violations = 0
            for fs_id in hyp.get('related_foreshadowings', []):
                cons = self.cg.get_weighted_consequences(fs_id, max_depth=3)
                for ctype, targets in cons.items():
                    for _, w in targets:
                        total_weight += w
                    if ctype == '矛盾/互斥':
                        rigid_violations += len(targets)

            # 3. 综合得分
            evidence_score = min(100, total_weight / max(1, len(hyp.get('related_foreshadowings', [1]))))
            final_score = (cao_eval['cao_score'] * 0.6 +
                          evidence_score * 0.3 -
                          rigid_violations * 10)

            results.append({
                'label': hyp['label'],
                'description': hyp['description'],
                'cao_score': cao_eval['cao_score'],
                'evidence_score': round(evidence_score, 1),
                'constraint_support': round(total_weight, 1),
                'rigid_violations': rigid_violations,
                'final_score': round(final_score, 1),
                'cao_eval_detail': cao_eval,
            })

        # Sort by final score descending
        results.sort(key=lambda x: x['final_score'], reverse=True)
        return results


# ============================================================
# 实时重载引擎
# ============================================================

class LiveEngine:
    """
    实时重载引擎 — 监控数据文件的变更并自动重新加载。

    用于社区协作场景：当有人提交新的伏笔/约束/人物数据后，
    引擎自动检测文件变化并重新计算所有权重和推理结果。
    """

    def __init__(self, data_dir: str, check_interval: int = 30):
        self.data_dir = data_dir
        self.check_interval = check_interval
        self.last_modified: Dict[str, float] = {}
        self._scan_files()

        # Load all components
        self.scholar = ScholarCredibility(data_dir)
        self.cao_model = CaoXueqinModel(data_dir)
        self.cg = WeightedConstraintGraph(self.scholar)
        self.comparator = None  # Lazy init

        self._load_all_data()

    def _scan_files(self):
        """记录所有数据文件的修改时间"""
        for root, _, files in os.walk(self.data_dir):
            for f in files:
                if f.endswith('.json'):
                    fp = os.path.join(root, f)
                    self.last_modified[fp] = os.path.getmtime(fp)

    def check_reload(self) -> List[str]:
        """检查是否有文件被更新，返回变更的文件列表"""
        changed = []
        for root, _, files in os.walk(self.data_dir):
            for f in files:
                if f.endswith('.json') and ('batch' in f or f.startswith('cao') or f.startswith('scholar')):
                    fp = os.path.join(root, f)
                    try:
                        mtime = os.path.getmtime(fp)
                        if fp not in self.last_modified or mtime > self.last_modified[fp]:
                            changed.append(fp)
                            self.last_modified[fp] = mtime
                    except FileNotFoundError:
                        pass

        if changed:
            self.reload()
        return changed

    def reload(self):
        """完全重新加载所有数据并重新计算权重"""
        self.scholar = ScholarCredibility(self.data_dir)
        self.cao_model = CaoXueqinModel(self.data_dir)
        self.cg = WeightedConstraintGraph(self.scholar)
        self._load_all_data()

    def _load_all_data(self):
        """加载所有数据到加权约束图"""
        # 简化版——实际使用时需要加载完整的 DataLoader
        pass

    def evaluate_new_hypothesis(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """完整评估一个新提交的假说"""
        cao_eval = self.cao_model.evaluate_hypothesis(
            hypothesis.get('description', ''),
            supporting_evidence=hypothesis.get('related_foreshadowings', [])
        )
        return {
            **cao_eval,
            'recommendation': (
                '此人选可加入' if cao_eval['cao_score'] >= 70
                else '此人选需更多证据' if cao_eval['cao_score'] >= 40
                else '此人选建议重新考虑'
            )
        }


# ============================================================
# CLI 演示 v2.0
# ============================================================

if __name__ == '__main__':
    import sys
    data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

    # Demo 1: Scholar credibility weighting
    print('=' * 65)
    print('  红楼梦伏笔约束推理引擎 v2.0')
    print('  —— 加权约束传播 + 曹雪芹风格检验')
    print('=' * 65)

    scholar = ScholarCredibility(data_dir)
    cao = CaoXueqinModel(data_dir)
    cg = WeightedConstraintGraph(scholar)

    # Load constraints from batch1 and batch2
    for batch in ['constraints.json', 'constraints_batch2.json']:
        try:
            path = os.path.join(data_dir, batch)
            with open(path, 'r', encoding='utf-8') as f:
                lst = json.load(f)
                if isinstance(lst, list):
                    cs = lst
                else:
                    cs = lst.get('constraints', [])
                for c in cs:
                    class C:
                        def __init__(self, d): self.__dict__.update(d)
                    cobj = C(c)
                    # Normalize field names
                    cobj.source = c.get('sourceForeshadowing', c.get('source', ''))
                    cobj.target = c.get('targetForeshadowingOrFate', c.get('target', ''))
                    cg.add_constraint(cobj)
        except FileNotFoundError:
            pass

    print(f'\n[*] 已加载 {len(cg.constraints)} 条约束（带权重）')
    print(f'[*] 曹雪芹模型: {len(cao.rigid_rules)} 条刚性约束, '
          f'{len(cao.strong_rules)} 条强度约束')

    # Demo 2: Evaluate competing hypotheses for 黛玉's death
    print('\n' + '=' * 65)
    print('  【多假设对比：林黛玉死法】')
    print('=' * 65)

    hypotheses = [
        {
            "label": "泪尽病逝说（主流）",
            "description": "黛玉因宝玉罹难急痛忧忿加速泪尽，十七岁春末病逝。死亡过程平静、无怨恨，正是万苦不怨。死后或许在太虚幻境与宝玉重逢。",
            "character_id": "CHAR-02",
            "related_foreshadowings": ["FS-002", "FS-003", "FS-013", "FS-026", "FS-038"],
        },
        {
            "label": "沉湖说（周汝昌）",
            "description": "黛玉践行质本洁来还洁去，在月夜投水身亡。冷月葬花魂即为谶语。全书多处水意象指向此。死亡方式是主动选择的自尽而非被动病逝。",
            "character_id": "CHAR-02",
            "related_foreshadowings": ["FS-003", "FS-009", "FS-026"],
        },
        {
            "label": "焚稿断情说（程高本）",
            "description": "黛玉在宝玉被骗娶宝钗的同一时刻焚毁诗稿，含恨而死。死亡过程中充满对宝玉的怨恨和对命运的控诉。",
            "character_id": "CHAR-02",
            "related_foreshadowings": ["FS-003"],
        },
    ]

    for hyp in hypotheses:
        result = cao.evaluate_hypothesis(hyp['description'])
        print(f"\n  [{result['verdict']}] {hyp['label']}")
        print(f"    曹雪芹符合度: {result['cao_score']}/100")
        if result['violations']:
            for v in result['violations']:
                print(f"    ⚠️ 违反约束 [{v['level']}]: {v['rule'][:60]}...")
        if result['style_notes']:
            for sn in result['style_notes']:
                print(f"    📝 风格问题 [{sn['dimension']}]: {sn['issue']}")

    # Demo 3: Weighted constraint propagation
    print('\n' + '=' * 65)
    print('  【加权约束传播：FS-017 → 四出戏谶】')
    print('=' * 65)

    cons = cg.get_weighted_consequences('FS-017', max_depth=3)
    for ctype, targets in cons.items():
        print(f'\n  {ctype}:')
        for tid, weight in sorted(targets, key=lambda x: x[1], reverse=True)[:8]:
            bar = '█' * int(weight / 5)
            print(f'    [{weight:3.0f}] {bar} {tid}')

    print('\n' + '=' * 65)
    print('  引擎 v2.0 就绪。')