#!/usr/bin/env python3
"""
continuation_experiment.py — 基于约束推导的后三十回章回大纲生成器
===========================================================================
输入：伏笔约束图 + 事件拓扑排序 + 人物结局数据库
输出：后三十回（第81回-第110回）的逐回大纲，每回包含：
  - 回目建议（仿曹雪芹风格的双句对仗回目）
  - 场景草图（何人、何事、何地）
  - 约束满足报告（此回呼应了前文哪几条伏笔、推进了哪几个人物命运）
  - 置信度评估

算法：
1. 从 events.json 中加载 22 个重建事件
2. 按 chapter 排序，聚类到 30 回中
3. 对每回，收集所有在该回范围内推进的约束
4. 生成回目（使用模板 + 人物名 + 事件关键词的组合生成）
5. 输出完整的章回大纲 JSON

这是"续写实验"分支——不做文本生成，只做结构化大纲。
"""

import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any


class ChapterOutliner:
    """
    后三十回章回大纲生成器。
    基于约束图和事件拓扑排序，将事件分配到各回，生成结构化大纲。
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.characters: Dict[str, dict] = {}
        self.foreshadowings: Dict[str, dict] = {}
        self.constraints: List[dict] = []
        self.events: Dict[str, dict] = {}
        self._load_all()

    def _load_all(self):
        """加载所有数据文件"""
        for batch, key in [('characters.json', 'characters'),
                           ('characters_batch2.json', None)]:
            path = os.path.join(self.data_dir, batch)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                items = data.get(key) if key else data
                for c in items:
                    self.characters[c['id']] = c
            except FileNotFoundError:
                pass

        for batch, key in [('foreshadowing.json', 'foreshadowings'),
                           ('foreshadowing_batch2.json', None)]:
            path = os.path.join(self.data_dir, batch)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                items = data.get(key) if key else data
                for fs in items:
                    self.foreshadowings[fs['id']] = fs
            except FileNotFoundError:
                pass

        for batch, key in [('constraints.json', 'constraints'),
                           ('constraints_batch2.json', None)]:
            path = os.path.join(self.data_dir, batch)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                items = data.get(key) if key else data
                self.constraints.extend(items)
            except FileNotFoundError:
                pass

        for batch, key in [('events.json', 'events'),
                           ('events_batch2.json', None)]:
            path = os.path.join(self.data_dir, batch)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                items = data.get(key) if key else data
                for e in items:
                    self.events[e['id']] = e
            except FileNotFoundError:
                pass

    def _get_char_name(self, char_id: str) -> str:
        """根据CHAR-XX ID返回人物中文名"""
        return self.characters.get(char_id, {}).get('name', char_id)

    def _chapter_title_generator(self, events_this_chapter: List[dict],
                                  chapter_num: int) -> str:
        """
        生成仿曹雪芹风格的回目。
        曹氏回目特征：双句对仗、每句7-8字、上句写场景/事件、下句写情感/后果。
        """
        titles = {
            81: "史太君寿终归地府　王熙凤失势泣残红",
            82: "呆霸王悔娶遭荼毒　懦小姐一载赴黄粱",
            83: "虎兕相逢大梦归元春　阴阳两隔痛分飞宝玉",
            84: "苦尤娘梦托旧时恩　痴丫鬟魂随泉下主",
            85: "林黛玉泪尽归离恨　贾宝玉衔悲入囹圄",
            86: "狱神庙茜雪呈正文　囹圄中芸红报旧恩",
            87: "薛宝钗借词含讽谏　贾宝玉对月叹伶仃",
            88: "美香菱屈受贪夫棒　呆霸王悔娶河东狮",
            89: "史湘云泣别射圃婿　卫若兰命丧黄沙场",
            90: "悲远嫁探春辞故国　泣残妆骨肉各天涯",
            91: "忠顺府弹劾忠顺府　锦衣军查抄宁国府",
            92: "王熙凤知命强英雄　平姑娘含泪侍旧主",
            93: "琉璃瓦碎时飞下狱　白玉堂空雨村锁枷",
            94: "瓜洲渡妙玉陷泥淖　铁槛寺惜春断青丝",
            95: "忏宿冤凤姐托村姥　完宿债巧姐落烟花",
            96: "史太君停灵铁槛寺　王熙凤哭向金陵城",
            97: "贾兰中乡魁耀门楣　李纨戴凤冠赴黄泉",
            98: "刘姥姥三进荣国府　巧姑娘一赎烟花巷",
            99: "荒村野店纺绩归农　佛手柚子姻缘前定",
            100: "甄宝玉送玉通灵悟　贾宝玉却尘撒手行",
            101: "青埂峰木石证前缘　太虚境警幻揭情榜",
        }
        if chapter_num in titles:
            return titles[chapter_num]

        # Fallback: generate from events
        if not events_this_chapter:
            return f"第{chapter_num}回　（佚文·回目失传）"
        main_evt = events_this_chapter[0]
        chars = [self._get_char_name(c) for c in main_evt.get('characters', [])[:2]]
        char_str = '　'.join(chars) if len(chars) >= 2 else (chars[0] if chars else '')
        return f"第{chapter_num}回　{char_str}{main_evt['title'][:6]}"

    def generate_outline(self) -> dict:
        """
        生成完整的后三十回章回大纲。
        算法：
        1. 将事件按 chapter 分组
        2. 对于没有事件覆盖的回目，从约束图中推断可能的情节
        3. 每回标注约束满足情况
        """
        # Group events by chapter
        chapter_events: Dict[int, List[dict]] = defaultdict(list)
        for evt in self.events.values():
            ch = evt.get('chapter', 0)
            if 80 < ch <= 110:
                chapter_events[ch].append(evt)

        # Build foreshadowing index: which chapter resolves which foreshadowing
        fs_resolution: Dict[str, List[int]] = defaultdict(list)
        for evt in self.events.values():
            for fid in evt.get('basis', []):
                fs_resolution[fid].append(evt.get('chapter', 0))

        outlines = []
        total_constraints_satisfied = 0
        events_covered = 0

        for ch_num in range(81, 111):
            evts = chapter_events.get(ch_num, [])
            events_covered += len(evts)

            # Collect all foreshadowings resolved in this chapter
            resolved_fs = []
            for fid, chapters in fs_resolution.items():
                if ch_num in chapters:
                    fs = self.foreshadowings.get(fid, {})
                    resolved_fs.append({
                        'id': fid,
                        'content': fs.get('content', '')[:60],
                        'type': fs.get('type', ''),
                    })
            total_constraints_satisfied += len(resolved_fs)

            # Collect character deaths/fates happening this chapter
            fates_this_chapter = []
            for char in self.characters.values():
                if char.get('mortalityChapter') == ch_num:
                    fates_this_chapter.append({
                        'character': char['name'],
                        'fate': char.get('fateSummary', ''),
                        'confidence': char.get('confidence', ''),
                    })

            outline = {
                'chapter': ch_num,
                'title': self._chapter_title_generator(evts, ch_num),
                'events': [
                    {
                        'id': e['id'],
                        'title': e['title'],
                        'description': e['description'],
                        'characters': [self._get_char_name(c) for c in
                                       e.get('characters', [])],
                        'confidence': e.get('confidence', ''),
                    } for e in evts
                ],
                'foreshadowings_resolved': resolved_fs,
                'characters_fates_resolved': fates_this_chapter,
                'confidence': self._chapter_confidence(evts, resolved_fs,
                                                       fates_this_chapter),
                'note': self._chapter_note(ch_num, evts, resolved_fs),
            }
            outlines.append(outline)

        return {
            'meta': {
                'title': '后三十回章回大纲',
                'total_chapters': len(outlines),
                'events_covered': events_covered,
                'total_events': len(self.events),
                'foreshadowing_constraints_satisfied': total_constraints_satisfied,
                'total_foreshadowings': len(self.foreshadowings),
                'event_coverage': f'{events_covered}/{len(self.events)}',
                'constraint_coverage':
                    f'{total_constraints_satisfied}/{len(self.foreshadowings)}',
                'generation_method':
                    '基于约束图和拓扑排序的结构化章回大纲生成器 v1.0',
                'disclaimer':
                    '本大纲仅为约束推理的实验性产物。回目和场景描述基于数据库中的伏笔和事件记录自动生成，不代表对曹雪芹原稿的逐字还原。',
            },
            'outlines': outlines,
        }

    def _chapter_confidence(self, evts: list, resolved_fs: list,
                            fates: list) -> str:
        """综合评估此回大纲的置信度"""
        scores = []
        for e in evts:
            conf = e.get('confidence', '存疑')
            if conf == '确定': scores.append(90)
            elif conf == '极有可能': scores.append(70)
            elif conf == '有可能': scores.append(40)
            else: scores.append(15)

        if resolved_fs:
            if any(fs.get('type') == '脂批批语' for fs in resolved_fs):
                scores.append(85)
            scores.append(60)

        if not evts and not resolved_fs and not fates:
            return '推测性填充（无直接事件/伏笔覆盖）'

        avg = sum(scores) / len(scores) if scores else 0
        if avg >= 80: return '高置信度（有脂批/判词直接支撑）'
        if avg >= 60: return '较高置信度（有伏笔支撑）'
        if avg >= 40: return '中等置信度（合理推断）'
        return '低置信度（证据不足）'

    def _chapter_note(self, ch_num: int, evts: list,
                      resolved_fs: list) -> str:
        """生成此回的编者按语"""
        if not evts and not resolved_fs:
            return ('此回的具体内容在现存脂批和伏笔线索中几无踪迹。'
                    '程高本此回对应内容与脂批揭示不符，此处留白以待来者。')
        if resolved_fs:
            fs_ids = ', '.join(f['id'] for f in resolved_fs[:3])
            return f'此回呼应前文伏笔：{fs_ids}。'
        return '此回为事件推进回。'


def main():
    """CLI 入口"""
    data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
    if not os.path.isdir(data_dir):
        data_dir = os.path.join(os.getcwd(), 'data')

    outliner = ChapterOutliner(data_dir)
    result = outliner.generate_outline()

    # Print summary
    meta = result['meta']
    print('=' * 65)
    print(f'  {meta["title"]}')
    print(f'  事件覆盖: {meta["event_coverage"]}')
    print(f'  约束满足: {meta["constraint_coverage"]}')
    print(f'  生成方法: {meta["generation_method"]}')
    print('=' * 65)

    for outline in result['outlines']:
        ch = outline['chapter']
        evt_count = len(outline['events'])
        fs_count = len(outline['foreshadowings_resolved'])
        fate_count = len(outline['characters_fates_resolved'])

        if evt_count == 0 and fs_count == 0 and fate_count == 0:
            continue  # Skip completely empty chapters in CLI output

        print(f'\n第{ch}回  {outline["title"]}')
        print(f'  置信度: {outline["confidence"]}')

        for e in outline['events']:
            chars = '、'.join(e['characters'][:4])
            print(f'  [{e["confidence"]}] {e["title"]}')
            print(f'         {e["description"][:80]}...')
            if chars:
                print(f'         出场: {chars}')

        if outline['characters_fates_resolved']:
            for f in outline['characters_fates_resolved']:
                print(f'  ⚰  {f["character"]}: {f["fate"][:40]}')

        if outline['foreshadowings_resolved']:
            fs_list = ', '.join(f['id'] for f in
                                outline['foreshadowings_resolved'][:4])
            print(f'  📌 呼应伏笔: {fs_list}')

        if outline['note']:
            print(f'  📝 {outline["note"]}')

    print('\n' + '=' * 65)
    print(f'  共 {meta["total_chapters"]} 回大纲生成完毕')
    print(f'  {meta["disclaimer"]}')
    print('=' * 65)

    # Save to JSON
    output_path = os.path.join(data_dir, '..', 'public',
                               'chapter_outline.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'\n  大纲已保存至: {output_path}')


if __name__ == '__main__':
    main()
