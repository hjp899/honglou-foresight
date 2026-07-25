#!/usr/bin/env python3
"""
红楼梦伏笔约束推理引擎
=========================
基于结构化伏笔数据和逻辑约束，推理人物结局的一致性和事件序列。
这是整个项目的核心计算模块。

核心能力:
1. 约束传播 —— 给定一条伏笔为真，传播其对其他伏笔/结局的影响
2. 一致性检查 —— 检查一组结局假设是否与所有约束兼容
3. 结局排序 —— 基于时间顺序约束对事件进行拓扑排序
4. 矛盾检测 —— 找出与给定假设冲突的证据
"""

import json
import os
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field


# ============================================================
# 数据模型
# ============================================================

@dataclass
class Foreshadowing:
    id: str
    chapter: int
    type: str
    content: str
    confidence: str
    evidence_type: str
    related_characters: List[str]
    related_events: List[str]

@dataclass
class CharacterFate:
    id: str
    name: str
    fate_summary: str
    confidence: str
    supporting: List[str]
    contradicting: List[str]
    mortality_chapter: Optional[int]

@dataclass
class Constraint:
    id: str
    type: str  # 必然导致 | 支持 | 矛盾/互斥 | 时间顺序约束 | 因果依赖
    source: str
    target: str
    rationale: str
    strength: str  # 刚性 | 强 | 弱

@dataclass
class Event:
    id: str
    chapter: int
    title: str
    description: str
    characters: List[str]
    basis: List[str]
    confidence: str


# ============================================================
# 数据加载
# ============================================================

class DataLoader:
    """从 JSON 文件加载结构化数据"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir

    def _load_json(self, filename: str) -> dict:
        path = os.path.join(self.data_dir, filename)
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_foreshadowings(self) -> Dict[str, Foreshadowing]:
        data = self._load_json('foreshadowing.json')
        result = {}
        for item in data['foreshadowings']:
            result[item['id']] = self._parse_fs(item)
        # Merge batch2 if exists
        try:
            data2 = self._load_json('foreshadowing_batch2.json')
            for item in data2:
                result[item['id']] = self._parse_fs(item)
        except FileNotFoundError:
            pass
        return result

    def _parse_fs(self, item: dict) -> Foreshadowing:
        return Foreshadowing(
            id=item['id'],
            chapter=item['chapter'],
            type=item['type'],
            content=item['content'],
            confidence=item['confidence'],
            evidence_type=item['evidenceType'],
            related_characters=[c['id'] for c in item['relatedCharacters']],
            related_events=[e['id'] for e in item['relatedEvents']],
        )

    def load_characters(self) -> Dict[str, CharacterFate]:
        data = self._load_json('characters.json')
        result = {}
        self._parse_char_list(data['characters'], result)
        # Merge batch2 if exists
        try:
            data2 = self._load_json('characters_batch2.json')
            self._parse_char_list(data2, result)
        except FileNotFoundError:
            pass
        return result

    def _parse_char_list(self, items: list, result: dict):
        for item in items:
            cf = CharacterFate(
                id=item['id'],
                name=item['name'],
                fate_summary=item['fateSummary'],
                confidence=item['confidence'],
                supporting=item['supportingForeshadowings'],
                contradicting=item['contradictingForeshadowings'],
                mortality_chapter=item.get('mortalityChapter'),
            )
            result[cf.id] = cf

    def load_constraints(self) -> List[Constraint]:
        data = self._load_json('constraints.json')
        result = [self._parse_cst(c) for c in data['constraints']]
        # Merge batch2
        try:
            data2 = self._load_json('constraints_batch2.json')
            result.extend(self._parse_cst(c) for c in data2)
        except FileNotFoundError:
            pass
        return result

    def _parse_cst(self, c: dict) -> Constraint:
        return Constraint(
            id=c['id'], type=c['type'], source=c['sourceForeshadowing'],
            target=c['targetForeshadowingOrFate'],
            rationale=c['rationale'], strength=c['strength'],
        )

    def load_events(self) -> Dict[str, Event]:
        data = self._load_json('events.json')
        result = {}
        self._parse_evt_list(data['events'], result)
        try:
            data2 = self._load_json('events_batch2.json')
            self._parse_evt_list(data2, result)
        except FileNotFoundError:
            pass
        return result

    def _parse_evt_list(self, items: list, result: dict):
        for item in items:
            evt = Event(
                id=item['id'], chapter=item['chapter'], title=item['title'],
                description=item['description'], characters=item['characters'],
                basis=item['basis'], confidence=item['confidence'],
            )
            result[evt.id] = evt


# ============================================================
# 约束图
# ============================================================

class ConstraintGraph:
    """以图结构存储伏笔/结局/事件之间的约束关系"""

    def __init__(self):
        # 邻接表: source -> [(target, constraint_type, strength)]
        self.graph: Dict[str, List[Tuple[str, str, str]]] = defaultdict(list)
        # 反向邻接表: target -> [(source, constraint_type, strength)]
        self.reverse_graph: Dict[str, List[Tuple[str, str, str]]] = defaultdict(list)
        # 同义/等价关系: 组ID -> {节点ID...}
        self.equivalence_groups: List[Set[str]] = []

    def add_constraint(self, c: Constraint):
        self.graph[c.source].append((c.target, c.type, c.strength))
        self.reverse_graph[c.target].append((c.source, c.type, c.strength))

    def get_consequences(self, node: str, max_depth: int = 5) -> Dict[str, List[str]]:
        """
        从一个伏笔出发，传播约束，找出所有受影响的节点。
        以 BFS 遍历，按约束类型分组返回。
        """
        visited = {node}
        queue = deque([(node, 0)])
        results: Dict[str, List[str]] = defaultdict(list)

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue

            for target, ctype, strength in self.graph.get(current, []):
                results[ctype].append(target)
                if target not in visited:
                    visited.add(target)
                    queue.append((target, depth + 1))

        return dict(results)

    def get_supporting_evidence(self, node: str) -> List[Tuple[str, str, str]]:
        """获取所有支持某个结局/事件的伏笔"""
        return self.reverse_graph.get(node, [])

    def find_contradictions(self, hypothesis: Set[str]) -> List[Tuple[str, str, str]]:
        """
        检查一组假设中是否存在内部矛盾。
        如果节点 A 和节点 B 之间存在'矛盾/互斥'约束，则返回矛盾。
        """
        contradictions = []
        for node in hypothesis:
            for target, ctype, strength in self.graph.get(node, []):
                if ctype == '矛盾/互斥' and target in hypothesis:
                    contradictions.append((node, target, strength))
        return contradictions


# ============================================================
# 时间线推理
# ============================================================

class TimelineEngine:
    """基于时间顺序约束对事件进行拓扑排序"""

    def __init__(self, events: Dict[str, Event],
                 constraint_graph: ConstraintGraph,
                 foreshadowings: Dict[str, Foreshadowing] = None):
        self.events = events
        self.cg = constraint_graph
        self.foreshadowings = foreshadowings or {}

    def topological_sort(self) -> List[Event]:
        """
        对事件进行拓扑排序。
        1. 从约束图中提取时间顺序约束和因果依赖
        2. 将伏笔间的约束桥接到事件（通过事件的basis字段）
        3. 基于事件的chapter字段作为缺省排序
        构建 DAG 并返回拓扑序。
        """
        in_degree: Dict[str, int] = defaultdict(int)
        adjacency: Dict[str, List[str]] = defaultdict(list)

        # Build a map: foreshadowing_id -> set of event_ids it supports
        fs_to_events: Dict[str, Set[str]] = defaultdict(set)
        for evt_id, evt in self.events.items():
            for fs_id in evt.basis:
                fs_to_events[fs_id].add(evt_id)

        # Propagate FS-level constraints to events:
        # If FS_A has a time/causal constraint on FS_B,
        # then any event supported by FS_A must precede any event supported by FS_B
        for source_fs, targets in self.cg.graph.items():
            source_events = fs_to_events.get(source_fs, set())
            if not source_events:
                continue
            for target_ref, ctype, strength in targets:
                if ctype not in ('时间顺序约束', '因果依赖'):
                    continue
                # target_ref could be a FS ID, an event ID, or a character ID
                target_events = fs_to_events.get(target_ref, set())
                # Also check if target_ref is directly an event ID
                if target_ref in self.events:
                    target_events.add(target_ref)
                for se in source_events:
                    for te in target_events:
                        if se != te:
                            adjacency[se].append(te)
                            in_degree[te] += 1
                            if se not in in_degree:
                                in_degree[se] = in_degree.get(se, 0)

        # Also build edges based on chapter order as fallback for events
        # without explicit constraints
        sorted_by_chapter = sorted(self.events.values(), key=lambda e: e.chapter or 999)
        for i in range(len(sorted_by_chapter) - 1):
            a = sorted_by_chapter[i]
            b = sorted_by_chapter[i + 1]
            # Only add a -> b if b doesn't yet have a predecessor and a isn't already connected to b
            if b.id not in adjacency.get(a.id, []):
                adjacency[a.id].append(b.id)
                in_degree[b.id] += 1
                if a.id not in in_degree:
                    in_degree[a.id] = in_degree.get(a.id, 0)

        # Ensure all events are registered in in_degree
        for evt_id in self.events:
            if evt_id not in in_degree:
                in_degree[evt_id] = 0

        # Kahn's algorithm
        queue = deque([n for n in in_degree if in_degree[n] == 0])
        order = []

        while queue:
            node = queue.popleft()
            if node in self.events:
                order.append(self.events[node])
            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Add remaining events not reached (cycles or isolated)
        for node in in_degree:
            if in_degree[node] > 0:
                continue
            if node in self.events and self.events[node] not in order:
                order.append(self.events[node])

        return order

    def get_event_sequence(self) -> List[Dict[str, Any]]:
        """返回按时间排序的事件序列及每步的推理依据

        排序策略：
        1. 首先按 chapter 排序（探佚推算的回目）
        2. 然后在时间顺序约束和因果依赖约束中查找更精确的排序信息
        """
        # Simple approach: sort by chapter, with constraint-based overrides noted
        sorted_events = sorted(self.events.values(), key=lambda e: (e.chapter or 999, e.id))

        # Build a lookup: for each event, find events it depends on via chapter order
        result = []
        for i, evt in enumerate(sorted_events):
            prerequisites = []
            for source, targets in self.cg.graph.items():
                for target, ctype, strength in targets:
                    if target == evt.id and ctype in ('时间顺序约束', '因果依赖'):
                        prerequisites.append({
                            'from': source,
                            'type': ctype,
                            'strength': strength,
                        })

            result.append({
                'order': i + 1,
                'event_id': evt.id,
                'title': evt.title,
                'chapter': evt.chapter,
                'description': evt.description,
                'confidence': evt.confidence,
                'prerequisites': prerequisites,
            })
        return result


# ============================================================
# 结局一致性检查
# ============================================================

class ConsistencyChecker:
    """
    检查一组人物结局假设是否与所有已知伏笔约束一致。

    使用场景：
    - 你提出一个结局假设（如'黛玉沉湖而死'）
    - 检查它与所有已知伏笔、脂批是否矛盾
    - 列出支持证据和反对证据
    """

    def __init__(self, foreshadowings: Dict[str, Foreshadowing],
                 characters: Dict[str, CharacterFate],
                 constraints: List[Constraint],
                 events: Dict[str, Event]):
        self.foreshadowings = foreshadowings
        self.characters = characters
        self.events = events
        self.cg = ConstraintGraph()
        for c in constraints:
            self.cg.add_constraint(c)

    def check_character_fate(self, char_id: str) -> Dict[str, Any]:
        """对一个人物的既定结局做全面一致性检查"""
        if char_id not in self.characters:
            return {'error': f'未知人物: {char_id}'}

        char = self.characters[char_id]

        # 收集支持证据
        supporting = []
        for fs_id in char.supporting:
            if fs_id in self.foreshadowings:
                fs = self.foreshadowings[fs_id]
                supporting.append({
                    'id': fs_id,
                    'type': fs.type,
                    'content': fs.content[:80] + '...' if len(fs.content) > 80 else fs.content,
                    'evidence_type': fs.evidence_type,
                    'confidence': fs.confidence,
                })

        # 收集反对证据
        contradicting = []
        for fs_id in char.contradicting:
            if fs_id in self.foreshadowings:
                fs = self.foreshadowings[fs_id]
                contradicting.append({
                    'id': fs_id,
                    'type': fs.type,
                    'content': fs.content[:80] + '...' if len(fs.content) > 80 else fs.content,
                })

        # 传播约束：找出所有间接关联的伏笔
        consequences = {}
        for fs_id in char.supporting:
            cons = self.cg.get_consequences(fs_id, max_depth=3)
            for ctype, targets in cons.items():
                if ctype not in consequences:
                    consequences[ctype] = []
                consequences[ctype].extend(targets)
        # 去重
        for k in consequences:
            consequences[k] = list(set(consequences[k]))

        # 检查矛盾
        all_nodes = set(char.supporting + char.contradicting)
        contradictions = self.cg.find_contradictions(all_nodes)

        return {
            'character': char.name,
            'fate': char.fate_summary,
            'confidence': char.confidence,
            'supporting_evidence': supporting,
            'contradicting_evidence': contradicting,
            'constraint_consequences': consequences,
            'internal_contradictions': [
                {'source': s, 'target': t} for s, t, _ in contradictions
            ],
            'verdict': '一致' if not contradictions and not char.contradicting else '有争议',
        }

    def check_custom_hypothesis(self, hypothesis: str,
                                 related_characters: List[str],
                                 proposed_foreshadowings: List[str]) -> Dict[str, Any]:
        """
        检查一个自定义假设是否与系统数据一致。

        Parameters:
        - hypothesis: 假设描述文本
        - related_characters: 涉及的人物ID列表
        - proposed_foreshadowings: 假设所引用的伏笔ID列表
        """
        # 收集所有相关约束
        all_relevant = set(proposed_foreshadowings)
        for fs_id in proposed_foreshadowings:
            if fs_id in self.foreshadowings:
                fs = self.foreshadowings[fs_id]
                for cid in fs.related_characters:
                    if cid in self.characters:
                        all_relevant.update(self.characters[cid].supporting)
                        all_relevant.update(self.characters[cid].contradicting)

        # 检查矛盾
        contradictions = self.cg.find_contradictions(all_relevant)

        # 查找反对证据
        opposing = []
        for fs_id in all_relevant:
            if fs_id in self.foreshadowings:
                fs = self.foreshadowings[fs_id]
            else:
                continue
            for c in [c for c in self.cg.graph.get(fs_id, [])]:
                if c[1] == '矛盾/互斥':
                    opposing.append({
                        'from': fs_id,
                        'to': c[0],
                        'strength': c[2],
                    })

        return {
            'hypothesis': hypothesis,
            'contradictions_found': len(contradictions) > 0 or len(opposing) > 0,
            'contradictions': [
                {'source': s, 'target': t, 'strength': strength}
                for s, t, strength in contradictions
            ],
            'opposing_constraints': opposing,
            'verdict': '假设兼容' if not contradictions and not opposing else '假设存在矛盾',
        }


# ============================================================
# 便捷函数
# ============================================================

def load_engine(data_dir: str = None) -> Tuple[DataLoader, ConstraintGraph,
                                                 TimelineEngine, ConsistencyChecker]:
    """一键加载所有模块"""
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

    loader = DataLoader(data_dir)
    foreshadowings = loader.load_foreshadowings()
    characters = loader.load_characters()
    constraints_list = loader.load_constraints()
    events = loader.load_events()

    cg = ConstraintGraph()
    for c in constraints_list:
        cg.add_constraint(c)

    timeline = TimelineEngine(events, cg, foreshadowings)
    checker = ConsistencyChecker(foreshadowings, characters, constraints_list, events)

    return loader, cg, timeline, checker


# ============================================================
# CLI 演示
# ============================================================

if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
    loader, cg, timeline, checker = load_engine(data_dir)

    print('=' * 60)
    print('  红楼梦伏笔约束推理引擎 — CLI 演示')
    print('=' * 60)

    # 1. 展示人物结局一致性检查
    print('\n【人物结局一致性检查】\n')
    for char_id in ['CHAR-02', 'CHAR-10', 'CHAR-01']:
        result = checker.check_character_fate(char_id)
        print(f'  {result["character"]}: {result["fate"][:40]}...')
        print(f'    置信度: {result["confidence"]}')
        print(f'    支持证据: {len(result["supporting_evidence"])} 条')
        print(f'    反对证据: {len(result["contradicting_evidence"])} 条')
        print(f'    判定: {result["verdict"]}')
        print()

    # 2. 时间线推理
    print('\n【后三十回事件时间线（拓扑排序）】\n')
    timeline_result = timeline.get_event_sequence()
    for item in timeline_result:
        print(f'  第{item["order"]:2d}位  [{item["chapter"]:3d}回] {item["title"]}')
        print(f'        置信度: {item["confidence"]}')
        if item['prerequisites']:
            prereqs = ', '.join(p['from'] for p in item['prerequisites'])
            print(f'        前置约束: {prereqs}')
        print()

    # 3. 约束传播示例
    print('\n【约束传播：从 FS-017（四出戏谶）出发】\n')
    consequences = cg.get_consequences('FS-017', max_depth=3)
    for ctype, targets in consequences.items():
        print(f'  {ctype}:')
        for t in targets[:5]:
            print(f'    → {t}')
        if len(targets) > 5:
            print(f'    ... 共 {len(targets)} 条')
        print()

    # 4. 统计
    print('=' * 60)
    print(f'  伏笔总数: {len(loader.load_foreshadowings())}')
    print(f'  人物总数: {len(loader.load_characters())}')
    print(f'  约束总数: {len(loader.load_constraints())}')
    print(f'  事件总数: {len(loader.load_events())}')
    print('=' * 60)
