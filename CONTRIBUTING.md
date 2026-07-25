# 贡献指南

欢迎任何形式的贡献！本项目最核心的资产是**数据**，而不是代码。每一条你录入的伏笔、补全的人物结局、建立的约束关系，都在直接增强整个系统的推理能力。

## 三种主要贡献方式

### 1. 添加新伏笔

在 `data/foreshadowing.json` 或新建 `data/foreshadowing_batch3.json` 中添加条目：

```json
{
  "id": "FS-061",
  "chapter": 34,
  "section": "情中情因情感妹妹",
  "type": "文本伏笔",
  "content": "此处填写前80回原文或脂批原文...",
  "context": "此处填写对这条伏笔的解读...",
  "evidenceType": "前80回文本伏笔",
  "confidence": "极有可能",
  "relatedCharacters": [{"id":"CHAR-XX","name":"人物名"}],
  "relatedEvents": [{"id":"EVT-XXX","name":"事件名"}],
  "source": "出处说明（版本、回目、批语位置）",
  "contributor": "你的GitHub ID"
}
```

**要求**：
- 伏笔内容必须源于前80回原文或脂批/畸笏批，不可自行编造
- 明确标注出处（哪个抄本的哪条批语、第几回第几段）
- 不确定的地方标注 `"confidence": "存疑"`

### 2. 添加新人物结局

在 `data/characters_batch2.json` 或新建的文件中添加：

```json
{
  "id": "CHAR-XX",
  "name": "人物名",
  "alias": ["别名"],
  "significance": "重要",
  "fateSummary": "结局一句话概述",
  "fateDetail": "结局详细描述及推理过程...",
  "confidence": "极有可能",
  "alternativeTheories": [
    {
      "theory": "替代学说名",
      "proponent": "提出者",
      "confidence": "有可能",
      "description": "该学说的详细内容..."
    }
  ],
  "supportingForeshadowings": ["FS-XXX"],
  "contradictingForeshadowings": [],
  "mortalityChapter": null,
  "lastChapterAppeared": 80,
  "quote": "代表性的判词/曲/谶语"
}
```

**置信度标准**：
- 确定 — 脂批直接提示，或文本内逻辑必然
- 极有可能 — 多条独立证据链汇聚
- 有可能 — 合理推测但证据不足
- 存疑 — 争议观点或纯推测

### 3. 添加新约束

在 `data/constraints_batch2.json` 或新建的文件中添加：

```json
{
  "id": "CST-00XX",
  "type": "支持",
  "sourceForeshadowing": "FS-XXX",
  "targetForeshadowingOrFate": "CHAR-XX",
  "rationale": "你的逻辑推理依据...",
  "strength": "强（极可能）"
}
```

**五种约束类型**：
- `必然导致` — 前提成立时结论必然成立（需要最严格的逻辑验证）
- `支持` — 前提增加了结论的可信度
- `矛盾/互斥` — 两个结论不能同时为真
- `时间顺序约束` — 事件A必须在事件B之前发生
- `因果依赖` — 事件A是事件B的前提条件

**约束强度**：刚性（逻辑必然） > 强（极可能） > 弱（可能支持）

## 提交流程

1. Fork 本仓库
2. 在新分支上进行修改
3. 确保 JSON 格式正确（可用 `python3 -c "import json; json.load(open('你的文件.json'))"` 验证）
4. 发 PR，附上简短说明
5. 如果是伏笔数据，请在 PR 中引用原文/脂批出处

## 数据质量原则

1. **第一优先：前80回原文** — 不可动摇的证据基础
2. **第二优先：脂批/畸笏批** — 同时代读过全稿的人
3. **第三优先：红学大家学术共识** — 多人独立得出的共同结论
4. **第四优先：顶级学者个人观点** — 标注提出者
5. **批判性采纳** — 与原文和脂批矛盾的观点降低权重，但不直接删除

## 特别提醒

- 周汝昌先生的"湘云嫁宝玉说"与脂批"卫若兰射圃"直接矛盾→标注为"存疑"
- 刘心武先生的"秦学体系"在红学界未被广泛接受→标注为"争议观点"
- 程高本后40回的情节不能作为证据使用（脂批已证实原稿后30回与续书不同）
- 网络/自媒体来源的观点需标注为"非学术来源"，一般不予录入

## 运行引擎验证

```bash
# 验证你的数据能被引擎正确加载
cd src/core
python3 engine.py

# 运行 v2.0 加权推理引擎
python3 engine_v2.py
```

## 获得帮助

如果你有某条伏笔或约束不确定是否应该加入，可以在 Issue 区发起讨论，附上你的原文/脂批依据和初步推理。
