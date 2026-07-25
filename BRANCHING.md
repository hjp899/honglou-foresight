# 分支策略与协作工作流

## 分支架构

```
main ──────────────────────────────►  生产分支（只接受 PR 合并）
  │
  ├── staging ─────────────────────►  集成测试分支（自动运行验证）
  │     │
  │     ├── community-foreshadowing ►  社区伏笔数据贡献
  │     ├── community-characters ───►  社区人物结局贡献
  │     ├── community-constraints ──►  社区约束关系贡献
  │     ├── engine-improvements ────►  推理引擎改进
  │     └── frontend-enhancements ──►  前端页面改进
  │
  └── gh-pages ────────────────────►  自动发布（GitHub Actions 自动同步）
```

## 各分支职责

### `main` — 生产分支（受保护）
- 只接受 Pull Request 合并，禁止直接 push
- 每个 PR 必须通过 CI 验证（JSON 格式检查 + 引擎一致性测试 + 跨文件引用完整性检查）
- 每次合并到 main 自动触发 GitHub Pages 部署

### `staging` — 集成测试分支
- 所有社区贡献先合并到这里
- 自动运行全套验证（JSON schema、约束图一致性、贝叶斯传播收敛）
- PR 从 staging 到 main 需要在 staging 上通过验证 + 至少一位维护者审核

### `community-foreshadowing` — 伏笔数据贡献
- 社区成员 fork 后在此分支提交 PR
- 新增伏笔的 JSON 条目模板在 CONTRIBUTING.md 中
- 通过 CI 验证后合并到 staging

### `community-characters` — 人物结局贡献
- 新人物结局、替代学说、证据补充
- 通过 CI 验证后合并到 staging

### `community-constraints` — 约束关系贡献
- 新增或修订伏笔间的逻辑约束
- 需要附上推理依据（rationale），否则 CI 拒绝

### `engine-improvements` — 引擎改进
- Python 推理引擎的算法优化
- 必须通过回归测试（与现有输出对比，差异不超过阈值）

### `frontend-enhancements` — 前端改进
- HTML/CSS/JS 修改
- 需要截图对比

### `gh-pages` — 自动发布
- 由 GitHub Actions 自动维护
- 禁止手动修改

---

## PR 提交流程（以添加新伏笔为例）

```bash
# 1. Fork 仓库
# 2. 克隆你的 fork
git clone https://github.com/YOUR_USERNAME/honglou-meng-foreshadowing.git
cd honglou-meng-foreshadowing

# 3. 切换到正确的分支
git checkout community-foreshadowing
git pull origin community-foreshadowing

# 4. 创建你的修改
#    (编辑 data/foreshadowing_batch3.json 或新建文件)

# 5. 本地验证（推荐先跑一下引擎）
cd src/core
python3 engine.py   # 确保你的新伏笔能被正确加载

# 6. 提交
git add data/
git commit -m "FS-061: 新增伏笔 — 第XX回 XXX批语 '...'"
git push origin community-foreshadowing

# 7. 在 GitHub 网页上发起 PR
#    base: staging  ← compare: community-foreshadowing
```

---

## 数据验证规则（CI 强制执行）

每次 PR 自动运行以下检查，全部通过才能合并：

### 1. JSON Schema 验证
```bash
python3 -c "
import json
for f in data/*.json:
    try: json.load(open(f)); print(f'{f}: OK')
    except: print(f'{f}: INVALID JSON'); exit(1)
"
```

### 2. ID 唯一性检查
- 所有 `FS-XXX`、`CHAR-XX`、`CST-XXXX`、`EVT-XXX` 在各自命名空间内不重复
- 公共 ID 前缀池检查（防止冲突）

### 3. 引用完整性检查
- 所有 `relatedCharacters` 和 `relatedEvents` 引用的 ID 在对应文件中存在
- 所有 `supportingForeshadowings` 和 `contradictingForeshadowings` 引用的 ID 存在
- 所有约束的 `sourceForeshadowing` 和 `targetForeshadowingOrFate` 引用的 ID 存在

### 4. 约束一致性检查
- 新增的约束不与已存在的刚性约束矛盾
- 如果新增约束标记为"必然导致"，引擎自动验证其是否与现有刚性约束兼容

### 5. 引擎回归测试
- 运行 `engine_v3.py` 并检查输出是否与基线一致
- 贝叶斯信念传播必须收敛（delta < 1e-6）
- MLN MAP 推断结果与当前共识的偏差不超过阈值

### 6. 曹雪芹风格检验
- 新人物结局的曹氏符合度必须 ≥ 40（否则标记为"待讨论"而非直接拒绝）
- 得分 40-69：允许合并但自动标注"存疑"
- 得分 < 40：阻止合并，需修改或提供更多证据

---

## GitHub Pages 部署

`gh-pages` 分支由 GitHub Actions 自动维护：

1. 每次 push 到 `main` 触发工作流
2. 工作流复制 `public/` 目录内容到 `gh-pages` 分支根目录
3. GitHub Pages 自动从 `gh-pages` 分支重新部署
4. 部署完成后自动检查 public/index.html 是否可访问
