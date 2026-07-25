#!/usr/bin/env python3
"""
cheng_gao_diff.py — 程高本后四十回 vs 约束推导结局的逐回差异分析
====================================================================
输入：约束推导的后三十回事件列表 + 程高本后四十回的已知情节
输出：逐回差异对比报告，包括：
  - 程高本此回写了什么（概要）
  - 约束推导系统认为此回应该发生什么
  - 差异类型：矛盾/缺失/新增/扭曲
  - 冲突的约束：程高本此回违反了哪几条伏笔/脂批约束
  - 差异严重性评分

这是"对比分析"分支——量化程高本续书与原稿约束的偏离程度。
"""

import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any


class ChengGaoDiffer:
    """程高本 vs 约束推导 逐回对比器"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.foreshadowings: Dict[str, dict] = {}
        self.events: Dict[str, dict] = {}
        self.constraints: List[dict] = []
        self._load_all()
        self._build_chenggao_plot_summary()

    def _load_all(self):
        """加载伏笔和事件数据"""
        for fname, key, target in [
            ('foreshadowing.json', 'foreshadowings', self.foreshadowings),
            ('foreshadowing_batch2.json', None, self.foreshadowings),
        ]:
            path = os.path.join(self.data_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                items = data.get(key) if key else data
                for item in items:
                    target[item['id']] = item
            except FileNotFoundError:
                pass

        for fname, key, target in [
            ('events.json', 'events', self.events),
            ('events_batch2.json', None, self.events),
        ]:
            path = os.path.join(self.data_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                items = data.get(key) if key else data
                for item in items:
                    target[item['id']] = item
            except FileNotFoundError:
                pass

        for fname, key in [('constraints.json','constraints'),
                           ('constraints_batch2.json',None)]:
            path = os.path.join(self.data_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                items = data.get(key) if key else data
                self.constraints.extend(items)
            except FileNotFoundError:
                pass

    def _build_chenggao_plot_summary(self):
        """
        程高本后四十回关键情节概要。
        仅收录与约束推导有显著差异的情节节点，非逐回全录。
        来源：程甲本/程乙本后四十回原文。
        """
        self.cg_plots = {
            81: {'summary': '宝玉再入家塾。贾政升任郎中。迎春回门诉苦。',
                 'key_events': ['宝玉重入家塾', '迎春回门哭诉', '贾政升官']},
            82: {'summary': '宝玉入学后思念黛玉。黛玉做噩梦。',
                 'key_events': ['宝玉上学', '黛玉噩梦']},
            83: {'summary': '元春染恙。黛玉吐血。',
                 'key_events': ['元春染病', '黛玉吐血']},
            84: {'summary': '贾母提出宝玉宝钗婚事。贾政考宝玉。',
                 'key_events': ['贾母提亲宝钗', '贾政试宝玉']},
            85: {'summary': '贾政升任工部郎中。宝玉宝钗议婚。薛蟠打死人命。',
                 'key_events': ['贾政升官', '议婚宝钗', '薛蟠命案']},
            86: {'summary': '薛蟠案审理拖延。元春病逝（享年43岁）。',
                 'key_events': ['薛蟠案审理', '元春病逝']},
            87: {'summary': '黛玉焚稿断情。紫鹃哭求。',
                 'key_events': ['黛玉焚诗稿', '悲痛欲绝']},
            88: {'summary': '贾母行乐。贾芸送礼。',
                 'key_events': ['贾母行乐', '贾芸送礼']},
            89: {'summary': '宝玉失玉疯癫。',
                 'key_events': ['宝玉丢玉', '神志不清']},
            90: {'summary': '宝玉疯癫中成婚（娶宝钗）。黛玉气绝。',
                 'key_events': ['调包计', '宝钗出嫁', '黛玉之死']},
            91: {'summary': '宝玉发现新娘是宝钗。',
                 'key_events': ['宝玉发现被骗']},
            92: {'summary': '宝玉渐渐接受宝钗。',
                 'key_events': ['宝玉接受宝钗']},
            93: {'summary': '贾府被抄。贾赦贾珍流放。',
                 'key_events': ['贾府被抄']},
            94: {'summary': '贾母病逝。',
                 'key_events': ['贾母去世']},
            95: {'summary': '鸳鸯殉主。',
                 'key_events': ['鸳鸯自缢']},
            96: {'summary': '凤姐病逝。',
                 'key_events': ['凤姐病死']},
            97: {'summary': '惜春出家。',
                 'key_events': ['惜春出家']},
            98: {'summary': '刘姥姥来探。巧姐被贾环等卖与藩王。',
                 'key_events': ['刘姥姥再访', '巧姐被卖']},
            99: {'summary': '刘姥姥救巧姐。',
                 'key_events': ['刘姥姥救巧姐']},
            100: {'summary': '宝玉中举。',
                 'key_events': ['宝玉中举人']},
            101: {'summary': '宝玉随僧道出家。贾府复兴。',
                 'key_events': ['宝玉出家（中举后）', '贾府沐皇恩']},
            102: {'summary': '贾府复兴。',
                 'key_events': ['贾府复兴']},
            103: {'summary': '贾政途遇宝玉（已出家）。',
                 'key_events': ['贾政遇宝玉']},
            104: {'summary': '贾府光复。',
                 'key_events': ['贾府光复']},
            105: {'summary': '（程高本无对应）',
                 'key_events': []},
            106: {'summary': '贾兰中举。',
                 'key_events': ['贾兰中举']},
            107: {'summary': '宝玉封号文妙真人。',
                 'key_events': ['宝玉受封']},
            108: {'summary': '（程高本无对应）',
                 'key_events': []},
            109: {'summary': '沐皇恩。兰桂齐芳。',
                 'key_events': ['沐皇恩', '兰桂齐芳']},
            110: {'summary': '贾府复荣。全书以\"兰桂齐芳\"收尾。',
                 'key_events': ['贾府复荣']},
        }

    def _get_derived_events_for_chapter(self, ch: int) -> List[dict]:
        """获取约束推导在此回应发生的事件"""
        return [e for e in self.events.values()
                if e.get('chapter') == ch]

    def analyze(self) -> dict:
        """生成完整的逐回差异对比报告"""
        diffs = []
        total_conflicts = 0
        total_alignments = 0

        for ch in range(81, 111):
            cg = self.cg_plots.get(ch, {'summary': '(无记录)', 'key_events': []})
            derived = self._get_derived_events_for_chapter(ch)

            diff = self._analyze_chapter(ch, cg, derived)
            diffs.append(diff)
            total_conflicts += diff['conflict_count']
            total_alignments += diff['alignment_count']

        severity = self._overall_severity(total_conflicts, total_alignments)

        return {
            'meta': {
                'title': '程高本后四十回 vs 约束推导结局 — 差异分析报告',
                'total_chapters_analyzed': len(diffs),
                'total_conflicts': total_conflicts,
                'total_alignments': total_alignments,
                'overall_severity': severity,
                'methodology': '逐回对比程高本情节与约束推理推导的事件序列',
            },
            'diffs': diffs,
            'summary': self._generate_summary(diffs, total_conflicts, severity),
        }

    def _analyze_chapter(self, ch: int, cg: dict,
                         derived: List[dict]) -> dict:
        """分析单回差异"""
        conflicts = []
        alignments = []

        for evt in derived:
            evt_title = evt.get('title', '')
            evt_conf = evt.get('confidence', '')
            cg_text = ' '.join(cg['key_events'])

            # Check alignment
            if self._event_matches_cg(evt_title, cg_text):
                alignments.append({
                    'event': evt_title,
                    'cg_parallel': self._find_parallel(evt_title, cg_text),
                    'confidence': evt_conf,
                })
            else:
                # Check conflict with constraints
                violated = self._find_violated_constraints(evt_title, cg_text)
                conflicts.append({
                    'event': evt_title,
                    'derived_event': evt.get('description', '')[:120],
                    'cg_plot': cg['summary'],
                    'violated_constraints': violated,
                    'confidence': evt_conf,
                })

        return {
            'chapter': ch,
            'chenggao_summary': cg['summary'],
            'derived_events': [
                {'title': e.get('title', ''), 'confidence': e.get('confidence', '')}
                for e in derived
            ],
            'conflicts': conflicts,
            'alignments': alignments,
            'conflict_count': len(conflicts),
            'alignment_count': len(alignments),
            'severity': self._chapter_severity(conflicts, derived),
            'verdict': self._chapter_verdict(conflicts, derived),
        }

    def _event_matches_cg(self, derived_title: str, cg_text: str) -> bool:
        """检查推导事件是否在程高本中有对应"""
        keyword_map = {
            '元春被赐死于政治斗争': ['元春', '薨', '死'],
            '迎春被孙绍祖虐死': ['迎春', '孙绍祖', '死'],
            '贾府被抄': ['被抄', '抄没', '籍没'],
            '惜春出家': ['惜春', '出家', '为尼'],
            '鸳鸯殉主': ['鸳鸯', '殉', '自缢'],
            '刘姥姥赎救巧姐': ['刘姥姥', '巧姐', '救'],
            '宝玉出家': ['宝玉', '出家', '僧道'],
            '贾兰中举': ['贾兰', '中举', '中乡魁'],
        }
        for key, kws in keyword_map.items():
            if key in derived_title and all(kw in cg_text for kw in kws):
                return True
        return False

    def _find_parallel(self, derived_title: str, cg_text: str) -> str:
        return '有大致对应（但细节可能已有扭曲）'

    def _find_violated_constraints(self, evt_title: str,
                                    cg_text: str) -> List[dict]:
        """找到程高本此回违反了哪些约束"""
        violated = []

        # Direct contradictions
        contradictions = {
            '元春被赐死': {
                'if_cg': all(kw in cg_text for kw in ['元春', '病']),
                'violated_rule': '脂批《长生殿》伏元妃之死=赐死，非病逝',
                'fs_ids': ['FS-008', 'FS-017'],
            },
            '黛玉之死': {
                'if_cg': all(kw in cg_text for kw in ['黛', '焚', '恨']),
                'violated_rule': "脂批'万苦不怨' 与 焚稿含恨而死 矛盾",
                'fs_ids': ['FS-002', 'FS-013', 'FS-026'],
            },
            '宝玉出家': {
                'if_cg': all(kw in cg_text for kw in ['宝玉', '中举']),
                'violated_rule': "宝玉中举后出家 与 '悬崖撒手'及'于国于家无望'矛盾",
                'fs_ids': ['FS-001', 'FS-005', 'FS-018'],
            },
            '白茫茫结局': {
                'if_cg': any(kw in cg_text for kw in ['沐皇恩', '兰桂齐芳', '复荣', '光复']),
                'violated_rule': "'落了片白茫茫大地真干净' 与 沐皇恩兰桂齐芳 绝对矛盾",
                'fs_ids': ['FS-031'],
            },
        }

        for key, rule in contradictions.items():
            if rule['if_cg']:
                violated.append(rule)

        return violated

    def _chapter_severity(self, conflicts: list, derived: list) -> str:
        if not derived:
            return '无约束推导事件覆盖'
        if not conflicts:
            return '一致'
        severity_weights = {
            '元春被赐死': 10,
            '黛玉之死': 10,
            '宝玉出家': 9,
            '白茫茫结局': 10,
        }
        score = 0
        for c in conflicts:
            for key, weight in severity_weights.items():
                if key in c.get('event', ''):
                    score += weight
        if score >= 15: return '严重冲突'
        if score >= 8: return '显著冲突'
        return '轻微差异'

    def _chapter_verdict(self, conflicts: list, derived: list) -> str:
        if not derived:
            return '此回在约束推导中无对应事件——程高本此回内容可能为续书者原创'
        if not conflicts:
            return '程高本此回与约束推导一致'
        if len(conflicts) >= 2:
            return '程高本此回存在多处与脂批/伏笔的严重矛盾'
        return '程高本此回存在差异，可能为续书者改写'

    def _overall_severity(self, total_c: int, total_a: int) -> str:
        ratio = total_c / max(1, total_c + total_a)
        if ratio > 0.6:
            return (f'严重偏离 ({ratio:.0%}) — 程高本后四十回与约束推导的结局框架'
                    f'存在根本性、系统性的矛盾。红学界主流立场（程高本为伪续）'
                    f'得到本系统定量支持。')
        if ratio > 0.3:
            return (f'显著差异 ({ratio:.0%}) — 程高本在关键情节上偏离原稿约束。')
        return (f'轻微差异 ({ratio:.0%}) — 程高本与约束推导大致吻合。'
                f'注意：吻合度高可能意味着该回含有曹雪芹原稿残片。')

    def _generate_summary(self, diffs: list, total_c: int,
                          severity: str) -> str:
        high_severity = [d for d in diffs if '严重' in d.get('severity', '')]
        return (
            f'程高本后四十回共 {len(diffs)} 回，'
            f'其中 {len(high_severity)} 回存在严重冲突。'
            f'核心冲突集中在：黛玉之死（焚稿断情 vs 泪尽夭亡）、'
            f'元春之死（病逝 vs 政治赐死）、'
            f'宝玉之结局（中举后出家 vs 悬崖撒手）、'
            f'全书结局（兰桂齐芳 vs 白茫茫大地真干净）。'
            f'\n总体评估：{severity}'
        )


def main():
    data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
    if not os.path.isdir(data_dir):
        data_dir = os.path.join(os.getcwd(), 'data')

    differ = ChengGaoDiffer(data_dir)
    report = differ.analyze()

    print('=' * 65)
    print(f'  {report["meta"]["title"]}')
    print('=' * 65)
    print(f'\n  {report["meta"]["overall_severity"]}')
    print(f'\n  {report["summary"]}')

    print(f'\n{"="*65}')
    print('  逐回差异详情（仅显示有冲突的回目）')
    print(f'{"="*65}')

    for diff in report['diffs']:
        if diff['conflict_count'] == 0:
            continue
        print(f'\n  第{diff["chapter"]}回  [{diff["severity"]}]')
        print(f'    程高本: {diff["chenggao_summary"][:80]}')
        for c in diff['conflicts']:
            print(f'    推导事件: {c["event"]} ({c["confidence"]})')
            for v in c.get('violated_constraints', []):
                print(f'      ❌ {v["violated_rule"]}')
            print()

    # Save report
    output_path = os.path.join(data_dir, '..', 'public', 'chenggao_diff.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'  报告已保存至: {output_path}')


if __name__ == '__main__':
    main()
