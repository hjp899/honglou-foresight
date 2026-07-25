# 🏮 红楼伏笔 — 《红楼梦》结构化探佚推理系统

**伏笔 · 脂批 · 约束 · 推理 · 开源协作**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-blue)](.github/workflows/validate-and-deploy.yml)
[![Data](https://img.shields.io/badge/Data-60%20Foreshadowings-b8860b)](data/foreshadowing.json)

> 草蛇灰线，伏脉千里。—— 脂砚斋

---

## 📖 这是什么

一个**开源的结构化探佚推理系统**。我们不续写《红楼梦》——我们做的更底层：把曹雪芹在前 80 回中埋下的每一条伏笔、脂砚斋留下的每一条批语、红学家数十年的探佚成果，转化为**可计算、可验证、可追溯的结构化数据**。

核心假设：**曹雪芹已写完《红楼梦》全书（110回），后 30 回因借阅者"迷失"而佚失。** 但大量伏笔和脂批提供了足够的约束条件——这些约束本质上定义了一个**逻辑推理问题**。给定足够多的约束，后 30 回的结局框架在逻辑上是唯一确定的，或至多有少量分支。

### 与已有项目的关系

| 项目 | 方法 | 我们的补充价值 |
|------|------|--------------|
| [MiroFish](https://github.com/666ghj/MiroFish) | 多智能体社会仿真 | 提供结构化伏笔库作为 Agent 行为约束 |
| [OpenStory](https://github.com/ZJU-LLMs/OpenStory) | 角色沙盒演化 | 提供人物命运"必然后果"的约束注入 |
| [GraphRAG红学](https://github.com/Airmomo/graphrag-practice-chinese) | 知识图谱问答 | 提供高质量结构化节点和边 |

**我们不做续写文本生成——我们做的是续写的"地基"：推理所需的所有约束条件。**

---

## 🔬 方法论

详细版见 [RESEARCH.md](RESEARCH.md)。核心思路：

1. **伏笔结构化** — 前 80 回每条伏笔与脂批按统一格式录入（8 种伏笔类型 × 4 级置信度 × 29 个人物）
2. **约束图构建** — 5 种逻辑关系：必然导致、支持、矛盾/互斥、时间顺序、因果依赖
3. **约束传播** — BFS 遍历约束图，自动传播影响
4. **贝叶斯信念传播** — 在约束网络中迭代更新节点置信度，直到收敛
5. **马尔可夫逻辑网络** — 软约束最优满意度求解
6. **拓扑排序** — 基于时间顺序重建后三十回事件序列
7. **曹雪芹风格检验** — 任何新假说自动经过 8 条刚性约束 + 10 条强约束 + 4 个风格维度检验
8. **RACS 多维评分** — 8 个维度自动评估任何学者/来源的权威性

---

## ✨ 功能亮点

### 🔮 探佚成果页（实时更新）

**[📊 查看最新探佚结果](https://hjp899.github.io/honglou-meng-foreshadowing/results.html)**

社区每次合并新数据，探佚成果页自动刷新：
- 后三十回共识时间线（22 个重建事件，每个事件标注集成置信度分数）
- 29 个人物结局一览（每人标注证据条数和置信度）
- 开源贡献统计（约束数、刚性约束数、人均证据条数）

### 🕸️ 十二钗命运关系图谱

**[📊 查看人物关系图](https://hjp899.github.io/honglou-meng-foreshadowing/relationship-graph.html)**

D3.js 力导向图，19 个节点 × 25 条关系边。正册/副册分色标注，按置信度（确定/极有可能/存疑）区分大小。悬停查看结局摘要，点击跳转到独立人物详页。

### 👤 十三钗独立人物页

黛玉页为精装手写版（三种死法对比 + 完整证据链 + 约束关系 + 命运节点时间线）。其余 12 人（宝玉+宝钗+元春+探春+湘云+妙玉+迎春+惜春+凤姐+巧姐+李纨）由 Python 模板从数据库批量生成。所有页面通过顶部导航互相串联。

### 🤖 三版推理引擎

| 版本 | 核心能力 |
|------|---------|
| **v1.0** (`engine.py`) | 基础约束传播 + 拓扑排序 + 一致性检查 |
| **v2.0** (`engine_v2.py`) | 加权约束（基于学者权威性） + 曹雪芹风格检验 + 多假设并行对比 |
| **v3.0** (`engine_v3.py`) | **贝叶斯信念传播** + **马尔可夫逻辑网络** + **文本自动解析**（接收原文/脂批/论文文本 → 自动抽取结构化伏笔条目） + **RACS 评分器**（自动评估新学者权威性） |

### 📐 RACS 学者权威评分体系

**通式：RACS = (0.20·机构 + 0.18·发表渠道 + 0.15·引用影响 + 0.15·同行认可 + 0.10·共识一致 + 0.10·方法论 + 0.07·时效性 + 0.05·原始文献) × 10**

12 位学者已评分：冯其庸 96 分（T1）· 蔡义江 88（T2）· 张庆善 86（T2）· 周汝昌 85（曹学高/推理打折）· 刘心武 25（T6·仅存档参考）。

**[合作者模板](data/contributor_scholar_template.json)** — 填写学者信息和作品描述即可，引擎自动代入通式计算权重。无需手动打分。

### 🏛️ 学术文献背书

**[学术书目](data/academic_bibliography.json)** — 收录中国艺术研究院红楼梦研究所（最高权威，权重 100）、中国红楼梦学会（95）、《红楼梦学刊》（90，CSSCI 来源期刊）、社科院文学所（85）四大机构的 13 部核心著作。所有证据链标注出处。社科院等国家权威机构的参考价值内置为更高权重。

### 🛡️ CI/CD 质量保障

每次 PR 自动运行：JSON 格式校验 → ID 唯一性检查 → 跨文件引用完整性检查 → 引擎回归测试 → 贝叶斯收敛性验证。**全部通过才能合并到 main。** 合并后自动部署到 gh-pages。分支策略见 [BRANCHING.md](BRANCHING.md)。

---

## 📊 当前数据规模

| 类别 | 数量 |
|------|------|
| 结构化伏笔 | **60 条**（覆盖第 1-80 回） |
| 人物结局 | **29 人**（十二钗 + 副册 + 重要配角） |
| 逻辑约束 | **40 条**（5 种类型） |
| 重建事件 | **22 个**（后三十回时间线） |
| 独立人物页 | **13 个**（宝玉 + 十二钗正册） |
| 推理引擎 | **3 版**（v1.0 → v2.0 → v3.0） |
| 学者评分 | **12 人**（6 层梯队） |
| 学术背书 | **4 个机构 + 13 部著作** |
| 前端页面 | **15 个** |

---

## 🚀 快速开始

### 在线浏览

不需要安装任何东西：

- 🏠 [主目录](https://hjp899.github.io/honglou-meng-foreshadowing/) — 六面板（概览/人物/伏笔/约束/时间线/贡献）
- 📊 [探佚成果](https://hjp899.github.io/honglou-meng-foreshadowing/results.html) — 后三十回共识推演（实时更新）
- 🕸️ [关系图谱](https://hjp899.github.io/honglou-meng-foreshadowing/relationship-graph.html) — 十二钗命运网络
- 👤 [黛玉详页](https://hjp899.github.io/honglou-meng-foreshadowing/character-lin-daiyu.html) — 精装版独立人物页

### 本地运行

```bash
git clone https://github.com/hjp899/honglou-meng-foreshadowing.git
cd honglou-meng-foreshadowing

# 前端预览
cd public && python3 -m http.server 8000
# 浏览器打开 http://localhost:8000

# 运行推理引擎 v3.0
cd src/core && python3 engine_v3.py --demo
```

---

## 🤝 如何贡献

### 贡献方式一：添加新伏笔

在 `data/foreshadowing_batch3.json`（或新建文件）中添加：

```json
{
  "id": "FS-061",
  "chapter": 34,
  "type": "文本伏笔",
  "content": "此处填写前80回原文或脂批原文...",
  "context": "此处填写对这条伏笔的解读...",
  "evidenceType": "前80回文本伏笔",
  "confidence": "极有可能",
  "relatedCharacters": [{"id":"CHAR-02","name":"林黛玉"}],
  "relatedEvents": [{"id":"EVT-002","name":"黛玉泪尽夭亡"}],
  "source": "第三十四回·甲戌本脂批",
  "contributor": "你的GitHub ID"
}
```

### 贡献方式二：引入新学者

填写 [contributor_scholar_template.json](data/contributor_scholar_template.json) 模板。提供学者的机构、著作、同行评价、方法论描述。引擎自动计算 RACS 权重分数。

### 贡献方式三：建立新约束

在 `data/constraints_batch3.json` 中添加。5 种类型可选：必然导致 / 支持 / 矛盾/互斥 / 时间顺序约束 / 因果依赖。需附上推理依据。

### 贡献方式四：补全新人物

12 钗之后，还有副册/又副册/三副四副的大量人物待补全。

### 提交流程

1. Fork 本仓库
2. 在对应分支上创建修改
3. 确保 JSON 格式正确 + 本地 `python3 engine.py` 无错误
4. 发 PR → CI 自动验证 → 维护者审核 → 合并 → 探佚成果页自动更新

详见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [BRANCHING.md](BRANCHING.md)。

---

## 📐 数据质量原则

1. **第一优先：前 80 回原文** — 不可动摇的证据基础
2. **第二优先：脂批/畸笏批** — 同时代读过全稿的人，权重 85-95
3. **第三优先：红学大家学术共识** — 权重 75（中国红楼梦学会/红研所背书）
4. **第四优先：顶级学者个人观点** — 权重 40-55，按 RACS 公式加权
5. **第五优先：网络/非学术来源** — 权重 ≤10，一般不予录入
6. **批判性采纳** — 与原文和脂批矛盾的观点降低权重，由引擎自动标注

---

## 📁 项目结构

```
honglou-meng-foreshadowing/
├── data/                         ← 核心资产层（15 个 JSON）
│   ├── foreshadowing.json + batch2    ← 60 条伏笔
│   ├── characters.json + batch2       ← 29 个人物结局
│   ├── constraints.json + batch2      ← 40 条逻辑约束
│   ├── events.json + batch2           ← 22 个重建事件
│   ├── caoxueqin_profile.json         ← 曹雪芹个人档案 + 作者推理模型
│   ├── scholar_credibility.json       ← 学者权威性评级体系
│   ├── academic_bibliography.json     ← 学术文献背书（13 部核心著作）
│   ├── historical_context.json        ← 曹家历史与小说对照
│   ├── scoring_formula.json           ← RACS 多维评分通式（8 维 10 级）
│   ├── contributor_scholar_template.json ← 合作者模板
│   └── schema.json                    ← 数据模型定义
├── src/core/
│   ├── engine.py                      ← v1.0：基础约束传播
│   ├── engine_v2.py                   ← v2.0：加权 + 曹氏检验
│   └── engine_v3.py                   ← v3.0：贝叶斯 + MLN + 文本解析 + RACS
├── public/                            ← 15 个 HTML 前端页面
│   ├── index.html                     ← 主目录（六面板）
│   ├── results.html                   ← 探佚成果页（实时更新）
│   ├── relationship-graph.html        ← D3.js 人物关系图谱
│   └── character-*.html × 13          ← 独立人物详页
├── .github/workflows/                 ← CI/CD 自动验证 + 自动部署
├── README.md                          ← 本文件
├── RESEARCH.md                        ← 研究方法论
├── BRANCHING.md                       ← 分支策略
└── CONTRIBUTING.md                    ← 贡献指南
```

---

## ⚖️ 学术立场声明

本项目是一个社区协作的结构化数据项目，不代表任何学术机构的官方立场。

- 本项目以**中国艺术研究院红楼梦研究所**主持出版的 1982 年人文社《红楼梦》新校注本为前 80 回文本基准
- 脂批引文以冯其庸《脂砚斋重评石头记汇校》为版本对勘依据
- 2024 年靖藏本辨伪成果（高树伟《红楼梦靖藏本辨伪》，中华书局）已纳入——本项目不使用任何靖藏本独家批语
- 欧阳健"脂批伪本说"不被本项目采纳——但对其方法论提醒（对脂批保持审慎）予以尊重
- 本项目采用红学界主流立场：曹雪芹为唯一作者、程高本后四十回为伪续、全书 110 回（80+30）

---

## 📜 许可

MIT License — 数据基于公共领域的《红楼梦》前 80 回文本和脂砚斋批语。学术文献版权归原作者和出版社所有。
