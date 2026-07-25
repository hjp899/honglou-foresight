#!/usr/bin/env python3
"""
engine_v3.py — 带概率推理与文本解析的红楼伏笔推理引擎 v3.0

新增功能：
1. 贝叶斯信念传播 — 在约束网络中进行概率传播，更新节点置信度
2. 马尔可夫逻辑网络 — 软约束的最优满意度配置求解
3. 文本自动解析 — 接收用户上传的原文/脂批/论文文本，自动提取伏笔
4. 集成分数计算 — 综合曹氏检验 + 证据权重 + 学术共识

用法: python3 engine_v3.py [--demo | --parse "文本" | --score CHAR-XX]
"""

import json
import math
import os
import re
import sys
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


# ============================================================
# 贝叶斯信念传播
# ============================================================

class BayesianNetwork:
    """
    对约束网络的贝叶斯解释。
    节点有 {True, False} 两种状态。
    边通过势函数 ψ(source_state, target_state) 编码约束类型和强度。
    """

    def __init__(self):
        self.nodes: Dict[str, Dict[str, float]] = {}
        self.potentials: Dict[Tuple[str, str], Dict[Tuple[bool, bool], float]] = {}
        self.incoming: Dict[str, List[str]] = defaultdict(list)
        self.outgoing: Dict[str, List[str]] = defaultdict(list)
        self.messages: Dict[Tuple[str, str], Dict[bool, float]] = {}
        self.prior_beliefs: Dict[str, float] = {}

    def add_node(self, node_id: str, prior_true: float = 0.5):
        """prior_true: 先验置信度 (0-1)，从证据权重中计算"""
        self.nodes[node_id] = {'p_true': prior_true, 'p_false': 1.0 - prior_true}
        self.prior_beliefs[node_id] = prior_true

    def add_edge(self, source: str, target: str, constraint_type: str, strength: str):
        """根据约束类型和强度自动设置势函数"""
        sf = 1.0
        if strength.startswith('刚性'): sf = 1.0
        elif strength.startswith('强'): sf = 0.8
        else: sf = 0.5

        pot = {}

        if constraint_type == '必然导致':
            pot[(True, True)] = 1.0 * sf
            pot[(True, False)] = (1.0 - sf) * 0.1
            pot[(False, True)] = 0.5
            pot[(False, False)] = 1.0

        elif constraint_type == '支持':
            pot[(True, True)] = 1.0 * sf
            pot[(True, False)] = 1.0 - sf
            pot[(False, True)] = 0.7
            pot[(False, False)] = 1.0

        elif constraint_type == '矛盾/互斥':
            pot[(True, True)] = (1.0 - sf) * 0.01
            pot[(True, False)] = 1.0 * sf
            pot[(False, True)] = 1.0
            pot[(False, False)] = 1.0

        elif constraint_type in ('时间顺序约束', '因果依赖'):
            pot[(True, True)] = 1.0 * sf
            pot[(True, False)] = 0.5
            pot[(False, True)] = 0.3 if constraint_type == '因果依赖' else 0.7
            pot[(False, False)] = 1.0

        else:
            pot[(True, True)] = 0.8
            pot[(True, False)] = 0.2
            pot[(False, True)] = 0.5
            pot[(False, False)] = 1.0

        key = (source, target)
        self.potentials[key] = pot
        self.outgoing[source].append(target)
        self.incoming[target].append(source)
        self.messages[(source, target)] = {True: 0.5, False: 0.5}

    def belief_propagation(self, iterations: int = 10) -> Dict[str, float]:
        """Loopy BP: 迭代直到收敛或达到最大迭代次数"""
        n = len(self.nodes)
        if n == 0:
            return {}

        # Initialize messages to uniform
        for key in self.messages:
            self.messages[key] = {True: 0.5, False: 0.5}

        for _ in range(iterations):
            max_delta = 0.0
            for (s, t) in list(self.messages.keys()):
                old_msg = dict(self.messages[(s, t)])

                # Compute product of incoming messages to s (excluding from t)
                product = {True: 1.0, False: 1.0}
                for u in self.incoming[s]:
                    if u == t:
                        continue
                    msg = self.messages.get((u, s), {True: 0.5, False: 0.5})
                    product[True] *= msg[True]
                    product[False] *= msg[False]

                # Prior
                prior = self.prior_beliefs.get(s, 0.5)
                product[True] *= prior
                product[False] *= (1.0 - prior)

                # Marginals × potential sum
                new_msg = {True: 0.0, False: 0.0}
                pot = self.potentials.get((s, t), {})
                for x in [True, False]:
                    for y in [True, False]:
                        psi = pot.get((x, y), 0.5)
                        new_msg[y] += product[x] * psi

                # Normalize
                total = new_msg[True] + new_msg[False]
                if total > 0:
                    new_msg[True] /= total
                    new_msg[False] /= total
                else:
                    new_msg[True] = 0.5
                    new_msg[False] = 0.5

                self.messages[(s, t)] = new_msg
                delta = abs(old_msg[True] - new_msg[True])
                max_delta = max(max_delta, delta)

            if max_delta < 1e-6:
                break

        # Compute final beliefs
        beliefs = {}
        for node in self.nodes:
            product = {True: 1.0, False: 1.0}
            prior = self.prior_beliefs.get(node, 0.5)
            product[True] *= prior
            product[False] *= (1.0 - prior)
            for u in self.incoming[node]:
                msg = self.messages.get((u, node), {True: 0.5, False: 0.5})
                product[True] *= msg[True]
                product[False] *= msg[False]
            total = product[True] + product[False]
            if total > 0:
                beliefs[node] = product[True] / total
            else:
                beliefs[node] = 0.5

        return beliefs


# ============================================================
# 马尔可夫逻辑网络
# ============================================================

class MarkovLogicNetwork:
    """
    软约束最优满意度求解。
    公式: P(X=x) ∝ exp(Σ w_i · n_i(x))
    使用梯度上升近似找到最大后验 (MAP) 配置。
    """

    def __init__(self):
        self.formulas: List[Dict[str, Any]] = []
        self.nodes: Set[str] = set()

    def add_formula(self, node_a: str, node_b: str, formula_type: str,
                    weight: float):
        self.nodes.add(node_a)
        self.nodes.add(node_b)
        self.formulas.append({
            'a': node_a, 'b': node_b, 'type': formula_type, 'weight': weight,
        })

    def evaluate_config(self, assignment: Dict[str, bool]) -> float:
        """计算某个赋值的对数概率（未归一化）"""
        log_prob = 0.0
        for f in self.formulas:
            a_val = assignment.get(f['a'], False)
            b_val = assignment.get(f['b'], False)
            satisfied = False

            if f['type'] == '必然导致':
                satisfied = not a_val or b_val
            elif f['type'] == '支持':
                satisfied = not a_val or b_val
            elif f['type'] == '矛盾/互斥':
                satisfied = not (a_val and b_val)
            elif f['type'] in ('时间顺序约束', '因果依赖'):
                satisfied = not a_val or b_val
            else:
                satisfied = not (a_val and not b_val)

            if satisfied:
                log_prob += f['weight']
            else:
                log_prob -= f['weight'] * 0.5

        return log_prob

    def map_inference(self, initial: Dict[str, float] = None,
                      steps: int = 100) -> Dict[str, bool]:
        """贪心局部搜索近似 MAP"""
        if initial is None:
            assignment = {n: (True if hash(n) % 2 == 0 else False)
                         for n in self.nodes}
        else:
            assignment = {n: (p > 0.5) for n, p in initial.items()}

        best_score = self.evaluate_config(assignment)

        improved = True
        iteration = 0
        while improved and iteration < steps:
            improved = False
            iteration += 1
            for node in self.nodes:
                original = assignment[node]
                assignment[node] = not original
                new_score = self.evaluate_config(assignment)
                if new_score > best_score:
                    best_score = new_score
                    improved = True
                else:
                    assignment[node] = original

        return assignment


# ============================================================
# 文本自动解析
# ============================================================

class TextParser:
    """从用户提交的自然语言文本中抽取伏笔条目"""

    def __init__(self, characters_json: str, events_json: str):
        with open(characters_json, 'r', encoding='utf-8') as f:
            cdata = json.load(f)
        self.character_names = []
        self.character_aliases = {}
        for c in cdata.get('characters', []):
            self.character_names.append(c['name'])
            self.character_aliases[c['name']] = c.get('alias', [])

        # Also load batch2
        b2_path = characters_json.replace('characters.json', 'characters_batch2.json')
        try:
            with open(b2_path, 'r', encoding='utf-8') as f:
                b2 = json.load(f)
            for c in b2:
                self.character_names.append(c['name'])
                self.character_aliases[c['name']] = c.get('alias', [])
        except FileNotFoundError:
            pass

        # Build name→aliases lookup
        self.name_to_aliases = {}
        for name, aliases in self.character_aliases.items():
            self.name_to_aliases[name] = name
            for a in aliases:
                self.name_to_aliases[a] = name

    def parse(self, text: str) -> Dict[str, Any]:
        """对用户提交的文本进行伏笔解析"""
        result = {
            'status': 'ok',
            'chapters_found': self._extract_chapters(text),
            'characters_found': self._extract_characters(text),
            'foreshadowing_type': self._classify_type(text),
            'suggested_confidence': self._suggest_confidence(text),
            'suggested_evidence_type': self._suggest_evidence_type(text),
            'suggested_constraint_type': self._extract_constraint_type(text),
            'parsed_quote': self._extract_quote(text),
            'warnings': [],
        }
        return result

    def _extract_chapters(self, text: str) -> List[int]:
        chapters = []
        for m in re.finditer(r'第\s*([一二三四五六七八九十百千\d]+)\s*回', text):
            num_str = m.group(1).strip()
            try:
                chapters.append(int(num_str))
            except ValueError:
                pass
        return chapters

    def _extract_characters(self, text: str) -> List[str]:
        found = set()
        for name in self.character_names:
            if name in text:
                found.add(name)
        for alias, canonical in self.name_to_aliases.items():
            if alias in text and alias != canonical:
                found.add(canonical)
        return list(found)

    def _classify_type(self, text: str) -> str:
        if any(kw in text for kw in ['脂批', '批语', '批注', '眉批', '夹批', '侧批', '回前',
                                        '脂砚', '畸笏', '笏叟', '脂评']):
            return '脂批批语'
        if any(kw in text for kw in ['判词', '判曲', '谶', '灯谜']):
            return '谶语判词'
        if any(kw in text for kw in ['谐音', '命名', '名字']):
            return '命名谐音'
        if any(kw in text for kw in ['梦', '托梦', '梦见']):
            return '梦境预兆'
        if any(kw in text for kw in ['点戏', '戏文', '扮', '唱']):
            return '戏曲点题'
        if any(kw in text for kw in ['说道', '言', '曰', '道']) and any(
            kw in text for kw in ['谕', '预示', '伏', '暗示', '预言']):
            return '对话暗示'
        if any(kw in text for kw in ['物', '扇', '帕', '玉', '锁', '麒麟']):
            return '物事象征'
        return '文本伏笔'

    def _suggest_confidence(self, text: str) -> str:
        """根据文本中的关键词推荐置信度"""
        if any(kw in text for kw in ['脂批', '批语']):
            if any(kw in text for kw in ['伏', '后文', '后数十回', '后三十回']):
                return '确定'
            return '极有可能'
        if any(kw in text for kw in ['毫无疑问', '必然', '显然', '无疑']):
            return '极有可能'
        if any(kw in text for kw in ['可能', '也许', '或许', '推测', '猜测']):
            return '有可能'
        if any(kw in text for kw in ['疑问', '争议', '不确定']):
            return '存疑'
        return '有可能'

    def _suggest_evidence_type(self, text: str) -> str:
        if any(kw in text for kw in ['脂批', '批语', '脂砚', '畸笏']):
            return '脂批直接提示'
        if any(kw in text for kw in ['判词', '谶语', '判曲']):
            return '判词/谶语'
        if any(kw in text for kw in ['伏笔', '埋伏', '暗示', '草蛇灰线']):
            return '前80回文本伏笔'
        return '其他'

    def _extract_constraint_type(self, text: str) -> Optional[str]:
        if any(kw in text for kw in ['必然', '必定', '一定', '只能']):
            return '必然导致'
        if any(kw in text for kw in ['支持', '佐证', '印证', '证明', '说明']):
            return '支持'
        if any(kw in text for kw in ['矛盾', '冲突', '违背', '不一致', '不同']):
            return '矛盾/互斥'
        if any(kw in text for kw in ['之前', '先于', '然后', '随后', '之前', '之前发生']):
            return '时间顺序约束'
        if any(kw in text for kw in ['因为', '导致', '由于', '所以', '因此']):
            return '因果依赖'
        return None

    def _extract_quote(self, text: str) -> Optional[str]:
        quote_match = re.search(r'[「『"\'""]([^」』"\'\""]{10,})[」』"\'""]', text)
        if quote_match:
            return quote_match.group(1)
        return None


# ============================================================
# 集成分数计算
# ============================================================

class IntegrationScorer:
    """综合多种指标计算人物结局的"集成分数" """

    def __init__(self, caoxueqin_model_data: dict):
        self.cao_rigid = []
        self.cao_strong = []
        am = caoxueqin_model_data.get('author_model', {})
        self.cao_rigid = am.get('level_1_rigid', {}).get('rules', [])
        self.cao_strong = am.get('level_2_strong', {}).get('rules', [])

    def score(self, character_name: str, fate_description: str,
              evidence_weight_sum: float, community_vote: float = 50.0,
              scholarly_consensus: float = 50.0) -> Dict[str, Any]:
        """计算完整的集成分数"""

        # Cao model score
        cao_score = 100.0
        for rule in self.cao_rigid:
            if self._violates(rule, fate_description):
                cao_score -= 30
        for rule in self.cao_strong:
            if self._violates(rule, fate_description):
                cao_score -= 15
        cao_score = max(0, cao_score)

        evidence_score = min(100, evidence_weight_sum / max(1, 1.0) * 20)

        final = (cao_score * 0.4 + evidence_score * 0.3 +
                 community_vote * 0.2 + scholarly_consensus * 0.1)

        return {
            'character': character_name,
            'cao_model_score': round(cao_score, 1),
            'evidence_score': round(evidence_score, 1),
            'community_vote': round(community_vote, 1),
            'scholarly_consensus': round(scholarly_consensus, 1),
            'final_integration_score': round(final, 1),
        }

    def _violates(self, rule: str, description: str) -> bool:
        rule_patterns = {
            '全书以绝对悲剧收场': ('', ['团圆', '皆大欢喜', '复荣', '兰桂齐芳']),
            '宝玉最终出家': ('宝玉', ['还俗', '还家', '中举', '做官']),
            '黛玉之死不是焚稿断情': ('', ['焚', '含恨', '泄愤', '调包计']),
            '元春之死是政治赐死': ('元春', ['病逝', '善终', '寿终正寝']),
            '鸳鸯在贾母死后必然遭到贾赦报复': ('鸳鸯', ['善终', '幸福', '自由']),
            '秦可卿原稿为淫丧天香楼': ('秦可卿', ['病死', '自然死亡']),
        }
        for rule_key, (ctx, contra) in rule_patterns.items():
            if rule_key in rule:
                if ctx and ctx not in description:
                    continue
                for w in contra:
                    if w in description:
                        return True
        return False


# ============================================================
# CLI 演示 & 测试
# ============================================================

if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

    if '--demo' in sys.argv or len(sys.argv) == 1:

        print('=' * 65)
        print('  推理引擎 v3.0 — 贝叶斯信念传播 + 马尔可夫逻辑网络')
        print('=' * 65)

        # Demo 1: Bayesian Belief Propagation
        print('\n[1] 贝叶斯信念传播 — 黛玉死亡约束网络\n')

        bn = BayesianNetwork()
        bn.add_node('FS-002_还泪设定', 0.95)
        bn.add_node('FS-003_判词', 0.95)
        bn.add_node('FS-013_芙蓉诔', 0.90)
        bn.add_node('FS-038_茗玉小姐', 0.80)
        bn.add_node('CHAR-02_病逝说', 0.85)
        bn.add_node('CHAR-02_沉湖说', 0.40)

        bn.add_edge('FS-002_还泪设定', 'CHAR-02_病逝说', '必然导致', '刚性（逻辑必然）')
        bn.add_edge('FS-003_判词', 'CHAR-02_病逝说', '支持', '强（极可能）')
        bn.add_edge('FS-013_芙蓉诔', 'CHAR-02_病逝说', '支持', '强（极可能）')
        bn.add_edge('FS-038_茗玉小姐', 'CHAR-02_病逝说', '支持', '强（极可能）')
        bn.add_edge('FS-003_判词', 'CHAR-02_沉湖说', '支持', '弱（可能支持）')

        beliefs = bn.belief_propagation(iterations=15)

        for node, prob in sorted(beliefs.items(), key=lambda x: x[1], reverse=True):
            bar = '█' * int(prob * 30)
            label = node.replace('FS-', '伏笔').replace('CHAR-', '人物')
            if '沉湖' in node:
                print(f'  [{prob:.3f}] {bar} {label}')
            break

        for node, prob in sorted(beliefs.items(), key=lambda x: x[1], reverse=True):
            if '沉湖' in node:
                bar = '█' * int(prob * 30)
                label = node.replace('CHAR-02_', '')
                print(f'  [{prob:.3f}] {bar} {label}')
                break

        # Demo 2: Markov Logic Network
        print('\n[2] 马尔可夫逻辑网络 — 最优配置\n')

        mln = MarkovLogicNetwork()
        ml_nodes = [
            '宝玉_出家', '黛玉_泪尽', '宝钗_独居', '凤姐_被休',
            '贾府_被抄', '元春_赐死', '迎春_虐死',
        ]
        for n in ml_nodes:
            mln.nodes.add(n)

        mln.add_formula('元春_赐死', '贾府_被抄', '因果依赖', 3.0)
        mln.add_formula('贾府_被抄', '凤姐_被休', '因果依赖', 2.5)
        mln.add_formula('贾府_被抄', '黛玉_泪尽', '支持', 2.0)
        mln.add_formula('宝玉_出家', '宝钗_独居', '必然导致', 3.0)
        mln.add_formula('贾府_被抄', '宝玉_出家', '支持', 2.3)

        assignment = mln.map_inference()
        for node in sorted(mln.nodes):
            val = '✓' if assignment[node] else '✗'
            print(f'  {val} {node}')
        best_score = mln.evaluate_config(assignment)
        print(f'\n  最优配置对数概率: {best_score:.2f}')

        # Demo 3: Text Parsing
        print('\n[3] 文本自动解析示例\n')

        parser = TextParser(
            os.path.join(data_dir, 'characters.json'),
            os.path.join(data_dir, 'events.json'),
        )

        test_texts = [
            ("脂批示例",
             "庚辰本第十八回眉批：'《乞巧》伏元妃之死。'此条批语明确指出元春如杨贵妃被赐死。"),

            ("论文示例",
             "蔡义江认为，黛玉之死是'泪尽夭亡'而非'焚稿断情'。'至死不干，万苦不怨'的脂批可证明黛玉之死无怨恨。"),

            ("伏笔示例",
             "第二十八回宝玉与蒋玉菡互换汗巾，后又将大红汗巾系在袭人腰间。脂砚批云：此物伏袭人后文嫁与蒋玉菡。"),
        ]

        for label, text in test_texts:
            result = parser.parse(text)
            print(f'  [{label}]')
            print(f'    回目: {result["chapters_found"]}')
            print(f'    人物: {result["characters_found"]}')
            print(f'    伏笔类型: {result["foreshadowing_type"]}')
            print(f'    置信度: {result["suggested_confidence"]}')
            print(f'    证据类型: {result["suggested_evidence_type"]}')
            if result['suggested_constraint_type']:
                print(f'    约束类型: {result["suggested_constraint_type"]}')
            if result['parsed_quote']:
                print(f'    引文: {result["parsed_quote"][:60]}...')
            print()

        # Demo 4: Integration Score
        print('[4] 集成分数计算\n')

        cao_data = json.load(open(
            os.path.join(data_dir, 'caoxueqin_profile.json'), 'r', encoding='utf-8'))
        scorer = IntegrationScorer(cao_data)

        for char, desc, evw, cv, sc in [
            ('林黛玉', '泪尽夭亡，十七岁病逝，万苦不怨', 85, 80, 90),
            ('林黛玉', '焚稿断情，含恨而死', 30, 10, 5),
            ('林黛玉', '投水自尽，质本洁来还洁去', 50, 40, 30),
        ]:
            r = scorer.score(char, desc, evw, cv, sc)
            verdict = '✓' if r['final_integration_score'] >= 70 else ('△' if r['final_integration_score'] >= 40 else '✗')
            print(f'  {verdict} [{r["final_integration_score"]:.1f}] {desc[:30]}...')

        print('\n' + '=' * 65)
        print('  引擎 v3.0 就绪。')
