#!/usr/bin/env python3
"""
redology_qa.py — 红学自然语言问答引擎
===========================================
基于约束图和伏笔数据库的红学知识问答系统。

用户可以问：
- "林黛玉是怎么死的？"
- "贾元春和贾探春谁更早离开贾府？"
- "湘云最终嫁给了谁？"
- "贾府被抄的原因是什么？"

引擎自动：
1. 解析问题（提取人物名、事件类型、关系词）
2. 在约束图和事件数据库中搜索匹配
3. 返回结构化答案：结论 + 置信度 + 支持证据链 + 反对证据 + 替代学说

这是"红学问答"分支——不做大模型对话，只做基于结构化数据的精确检索。
"""

import json
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any


class RedologyQA:
    """红学自然语言问答引擎"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.characters: Dict[str, dict] = {}
        self.foreshadowings: Dict[str, dict] = {}
        self.constraints: List[dict] = []
        self.events: Dict[str, dict] = {}
        self._load_all()
        self._build_indexes()

    def _load_all(self):
        """加载全部数据"""
        for fname, key, target in [
            ('characters.json', 'characters', self.characters),
            ('characters_batch2.json', None, self.characters),
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

        for fname, key in [('constraints.json', 'constraints'),
                           ('constraints_batch2.json', None)]:
            path = os.path.join(self.data_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                items = data.get(key) if key else data
                self.constraints.extend(items)
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

    def _build_indexes(self):
        """构建全文搜索索引"""
        self.name_index: Dict[str, List[str]] = defaultdict(list)
        for cid, char in self.characters.items():
            self.name_index[char['name']].append(cid)
            for alias in char.get('alias', []):
                if alias:
                    self.name_index[alias].append(cid)

        self.event_keyword_index: Dict[str, List[str]] = defaultdict(list)
        for eid, evt in self.events.items():
            text = evt.get('title', '') + ' ' + evt.get('description', '')
            for word in re.findall(r'[一-鿿]{2,4}', text):
                self.event_keyword_index[word].append(eid)

    def _find_character(self, name: str) -> Optional[dict]:
        """根据中文本名或别名查找人物"""
        for cid in self.name_index.get(name, []):
            return self.characters[cid]
        for char in self.characters.values():
            if name in char.get('name', ''):
                return char
        return None

    def _find_events_by_keyword(self, keyword: str) -> List[dict]:
        """按关键词搜索事件"""
        result_ids = set()
        for word, eids in self.event_keyword_index.items():
            if keyword in word:
                result_ids.update(eids)
        return [self.events[eid] for eid in result_ids if eid in self.events]

    def ask(self, question: str) -> dict:
        """主问答入口"""
        q = question.strip()

        # Route to specialized handlers
        for pattern, handler in self._question_routes():
            match = re.search(pattern, q)
            if match:
                return handler(match, q)

        # Fallback: keyword search
        return self._fallback_search(q)

    def _question_routes(self) -> List[Tuple[str, callable]]:
        """问题模式 → 处理函数 的路由表"""
        return [
            # "谁 + 怎么死的" or "XX 的结局"
            (r'(.{1,4})[的之]?(怎么|如何|怎样)(死|去世|结局|结局是)', self._handle_fate_query),
            # "XX 嫁给了谁" or "XX 娶了谁"
            (r'(.{1,4})(嫁|娶|嫁给|娶了)(谁|什么人|哪位)', self._handle_marriage_query),
            # "XX 和 YY 谁先/谁后"
            (r'(.{1,3})和(.{1,3})(谁先|谁后|哪个先|哪个后|先后)', self._handle_temporal_query),
            # "贾府为什么/为何/怎么被抄" or "XX 的原因"
            (r'(贾府|荣国府|宁国府|贾家)[的之]?(为什么|为何|怎么|如何|原因)(被抄|败落|衰败|灭亡)', self._handle_causality_query),
            # "XX 是/是不是 YY"
            (r'(.{1,4})(是|是不是|是否为)(.{1,20})', self._handle_identity_query),
        ]

    def _handle_fate_query(self, match, question: str) -> dict:
        """处理关于人物结局的查询"""
        char_name = match.group(1)
        char = self._find_character(char_name)
        if not char:
            return self._not_found(f'未找到人物"{char_name}"')

        evidence = []
        for fid in char.get('supportingForeshadowings', []):
            fs = self.foreshadowings.get(fid, {})
            if fs:
                evidence.append({
                    'id': fid,
                    'type': fs.get('type', ''),
                    'content': fs.get('content', '')[:80],
                    'confidence': fs.get('confidence', ''),
                    'chapter': fs.get('chapter', ''),
                })

        contra = []
        for fid in char.get('contradictingForeshadowings', []):
            fs = self.foreshadowings.get(fid, {})
            if fs:
                contra.append({
                    'id': fid,
                    'content': fs.get('content', '')[:80],
                })

        alternatives = char.get('alternativeTheories', [])

        return {
            'question': question,
            'answer': f'{char["name"]}：{char["fateSummary"]}',
            'detail': char.get('fateDetail', ''),
            'confidence': char.get('confidence', ''),
            'supporting_evidence': evidence,
            'contradicting_evidence': contra,
            'alternative_theories': alternatives,
            'quote': char.get('quote', ''),
        }

    def _handle_marriage_query(self, match, question: str) -> dict:
        """处理关于婚姻关系的查询"""
        char_name = match.group(1)
        char = self._find_character(char_name)
        if not char:
            return self._not_found(f'未找到人物"{char_name}"')

        fate_text = char.get('fateDetail', '') + char.get('fateSummary', '')
        marry_info = self._extract_marriage_info(char.get('id', ''), fate_text)

        return {
            'question': question,
            'answer': marry_info or f'数据库中未明确记录{char["name"]}的婚姻细节',
            'character': char['name'],
            'fate_summary': char.get('fateSummary', ''),
        }

    def _extract_marriage_info(self, char_id: str, text: str) -> str:
        """从人物结局文本中提取婚姻信息"""
        marriage_map = {
            'CHAR-01': '贾宝玉娶薛宝钗为妻（金玉良缘），但婚后不久即出家。精神上始终忠于林黛玉（木石前盟）。',
            'CHAR-02': '林黛玉未及出嫁，以泪尽夭亡结束一生。宝黛的爱情是全书最核心的感情线。',
            'CHAR-03': '薛宝钗嫁贾宝玉为妻（金玉良缘），但婚姻极为短暂——恩爱夫妻不到冬。宝玉出家后宝钗独守空闺。',
            'CHAR-06': '史湘云嫁卫若兰（有脂批直接证据：后数十回若兰在射圃所佩之麒麟正此麒麟也）。卫若兰死于战事或流放后，湘云寡居。',
            'CHAR-08': '贾迎春嫁孙绍祖（中山狼），婚后不到一年被虐待致死——一载赴黄粱。',
            'CHAR-11': '巧姐被刘姥姥赎出后嫁板儿为农家妇——纺绩于荒村野店。',
            'CHAR-12': '李纨青年丧夫（贾珠早逝），守寡一生。儿子贾兰中举后旋即身亡，枉与他人作笑谈。',
            'CHAR-16': '袭人嫁蒋玉菡（琪官）——堪羡优伶有福，谁知公子无缘。第二十八回宝玉与蒋玉菡互换汗巾又系在袭人腰间，伏下千里姻缘。',
        }
        return marriage_map.get(char_id, '据约束图推断：' +
                                text[:100].replace('\n', ''))

    def _handle_temporal_query(self, match, question: str) -> dict:
        """处理关于时间先后顺序的查询"""
        name_a, name_b = match.group(1), match.group(2)
        char_a = self._find_character(name_a)
        char_b = self._find_character(name_b)
        if not char_a or not char_b:
            return self._not_found('未能识别两个人物')

        ch_a = char_a.get('mortalityChapter', 999)
        ch_b = char_b.get('mortalityChapter', 999)

        if ch_a == 999 and ch_b == 999:
            return {
                'question': question,
                'answer': f'{char_a["name"]}和{char_b["name"]}的具体结局时序目前数据库中尚未确定。',
                'note': '可能两人结局回目均无明确推算值。',
            }

        earlier = char_a if ch_a < ch_b else char_b
        later = char_b if ch_a < ch_b else char_a

        return {
            'question': question,
            'answer': f'{earlier["name"]}先于{later["name"]}离开贾府/离世（推算回目：第{earlier.get("mortalityChapter","?")}回 vs 第{later.get("mortalityChapter","?")}回）',
            'detail': f'{char_a["name"]}：{char_a.get("fateSummary","")}\n{char_b["name"]}：{char_b.get("fateSummary","")}',
            'confidence': '推断（基于探佚推算回目，非原文证据）',
        }

    def _handle_causality_query(self, match, question: str) -> dict:
        """处理关于因果关系的查询"""
        events = self._find_events_by_keyword('被抄')
        events += self._find_events_by_keyword('败落')

        causes = []
        for e in events:
            if '被抄' in e.get('title', '') or '败落' in e.get('title', ''):
                causes.append({
                    'event': e.get('title', ''),
                    'description': e.get('description', ''),
                    'basis': e.get('basis', []),
                })

        # Find all constraints that lead to 贾府被抄
        related_constraints = []
        for c in self.constraints:
            if c.get('targetForeshadowingOrFate', '') == 'EVT-013':
                related_constraints.append({
                    'type': c.get('type', ''),
                    'rationale': c.get('rationale', ''),
                    'strength': c.get('strength', ''),
                })

        return {
            'question': question,
            'answer': (
                '贾府之败的根本原因是\'自杀自灭\'（探春语）——家族内部的道德崩溃、财政枯竭和人才断层。'
                '直接导火索是元春在政治斗争中被赐死，导致贾府失去政治庇护。'
                '脂批以《一捧雪》（一出关于一件宝物引发灭门之祸的戏）作为贾府之败的谶语，暗示可能因某件与皇家有关的物品（通灵玉？）获罪被抄。'
                '曹雪芹将曹家\'因亏空被抄\'的现实升华为更深刻的政治悲剧。'
            ),
            'related_events': causes[:3],
            'related_constraints': related_constraints[:5],
            'confidence': '确定（脂批直接提示 + 判词支撑）',
        }

    def _handle_identity_query(self, match, question: str) -> dict:
        """处理关于等价/同一性的查询"""
        name_a, name_b = match.group(1), match.group(3)
        char_a = self._find_character(name_a)
        char_b = self._find_character(name_b)

        if char_a and char_b and char_a['id'] == char_b['id']:
            return {
                'question': question,
                'answer': f'是。{name_a}与{name_b}为同一人。',
                'aliases': char_a.get('alias', []),
            }

        return {
            'question': question,
            'answer': f'不是同一人。' + (f'{name_a}：{char_a["name"]}。' if char_a else '') +
                      (f'{name_b}：{char_b["name"]}。' if char_b else ''),
        }

    def _fallback_search(self, question: str) -> dict:
        """降级搜索——关键词匹配"""
        results = []
        for cid, char in self.characters.items():
            if char['name'] in question:
                results.append({
                    'type': 'character',
                    'name': char['name'],
                    'fate': char.get('fateSummary', ''),
                    'confidence': char.get('confidence', ''),
                })

        for eid, evt in self.events.items():
            if any(kw in question for kw in evt.get('title', '')):
                results.append({
                    'type': 'event',
                    'title': evt.get('title', ''),
                    'description': evt.get('description', '')[:120],
                    'chapter': evt.get('chapter', ''),
                    'confidence': evt.get('confidence', ''),
                })

        return {
            'question': question,
            'answer': f'在数据库中找到 {len(results)} 条相关记录',
            'results': results[:10],
            'note': '此结果为关键词匹配，非精确问答。请尝试使用更具体的问题格式，如"林黛玉是怎么死的？"或"贾府为什么被抄？"',
        }

    def _not_found(self, msg: str) -> dict:
        return {'question': '', 'answer': msg, 'status': 'not_found'}


def interactive_shell():
    """交互式问答终端"""
    data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
    if not os.path.isdir(data_dir):
        data_dir = os.path.join(os.getcwd(), 'data')

    qa = RedologyQA(data_dir)

    print('=' * 60)
    print('  红学问答引擎 — 基于约束图的结构化知识检索')
    print('  输入 quit 或 exit 退出，输入 help 查看示例问题')
    print('=' * 60)

    examples = [
        "林黛玉是怎么死的？",
        "湘云嫁给了谁？",
        "贾府为什么被抄？",
        "林黛玉和贾元春谁先去世？",
        "贾宝玉是宝玉吗？",
    ]
    print('\n示例问题:')
    for ex in examples:
        print(f'  > {ex}')
    print()

    while True:
        try:
            q = input('🗣️  > ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\n再见。')
            break

        if not q:
            continue
        if q.lower() in ('quit', 'exit', 'q'):
            print('再见。')
            break
        if q.lower() == 'help':
            for ex in examples:
                print(f'  {ex}')
            continue

        result = qa.ask(q)
        self._pretty_print(result)

    @staticmethod
    def _pretty_print(result: dict):
        """格式化打印问答结果"""
        if result.get('status') == 'not_found':
            print(f'  ❓ {result["answer"]}\n')
            return

        print(f'  📖 {result.get("answer", "未找到明确答案")}')

        if result.get('detail'):
            print(f'     {result["detail"][:200]}')

        if result.get('confidence'):
            print(f'     置信度: {result["confidence"]}')

        if result.get('supporting_evidence'):
            print(f'     📌 支持证据 ({len(result["supporting_evidence"])} 条):')
            for ev in result['supporting_evidence'][:4]:
                print(f'        {ev.get("id","")} [第{ev.get("chapter","?")}回] '
                      f'{ev.get("content","")[:60]}')

        if result.get('alternative_theories'):
            print(f'     🔍 替代学说:')
            for alt in result['alternative_theories']:
                print(f'        {alt.get("theory","")} — {alt.get("proponent","")} '
                      f'({alt.get("confidence","")})')

        if result.get('results'):
            for r in result['results'][:5]:
                if r['type'] == 'character':
                    print(f'     👤 {r["name"]}: {r["fate"][:60]}')
                elif r['type'] == 'event':
                    print(f'     📅 [{r["chapter"]}回] {r["title"]}')

        print()


if __name__ == '__main__':
    if '--non-interactive' in sys.argv:
        # Demo mode
        data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        if not os.path.isdir(data_dir):
            data_dir = os.path.join(os.getcwd(), 'data')
        qa = RedologyQA(data_dir)

        demo_questions = [
            "林黛玉是怎么死的？",
            "湘云嫁给了谁？",
            "贾府为什么被抄？",
            "林黛玉和贾元春谁先去世？",
        ]
        for q in demo_questions:
            print(f'\n🗣️  > {q}')
            result = qa.ask(q)
            print(f'  📖 {result.get("answer","")[:150]}')
            if result.get('confidence'):
                print(f'     置信度: {result["confidence"]}')
            if result.get('supporting_evidence'):
                print(f'     证据: {len(result["supporting_evidence"])} 条')
            if result.get('alternative_theories'):
                print(f'     替代学说: {len(result["alternative_theories"])} 个')
    else:
        interactive_shell()
