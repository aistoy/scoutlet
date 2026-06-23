# Scoutlet Benchmark 标注规范

## 1. 文档目的

本文定义 `docs/benchmark/queries.yaml` 中查询标注的字段、流程和质量要求。benchmark 用这些标注评估搜索召回和覆盖（详见 `agent_search_near_term_plan.md` §9.2）。

本规范**不要求构建完整事实答案**——只标注"期望域名"和少量已知相关 URL，足以计算 Recall@K 和 Relevant domains@K 即可。

## 2. 字段定义

每个查询是一个 YAML 对象。Schema 版本：`1`。

### 2.1 完整字段示例

```yaml
schema_version: 1
queries:
  - id: tech_001
    query: "python TaskGroup documentation"
    language: en
    subcategory: technical_docs
    expected_domains:
      - python.org
    known_relevant_urls:
      - https://docs.python.org/3/library/asyncio-taskgroup.html
    difficulty: medium
    annotator: ethan
    annotated_at: 2026-06-23
    last_reviewed_at: 2026-06-23
    notes: |
      Python 3.11+ asyncio feature. Official docs 是权威来源。
      Stack Overflow 有示例讨论但不计入 expected_domains。
```

### 2.2 字段语义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 全局唯一稳定标识，格式 `<subcategory_prefix>_<NNN>` |
| `query` | string | 是 | 查询文本，不含引号；保持用户真实输入形式 |
| `language` | enum | 是 | `en` / `zh` / 其他 ISO 639-1 代码 |
| `subcategory` | enum | 是 | 见 §3 |
| `expected_domains` | list[string] | 是 | 1–3 个 eTLD+1，结果中应出现 |
| `known_relevant_urls` | list[string] | 否 | 0–2 个具体 URL，用于精确 Recall 计算 |
| `difficulty` | enum | 否 | `easy` / `medium` / `hard`，影响定性分析 |
| `contested` | bool | 否 | 标注存在争议时设为 `true`，详见 §6 |
| `annotator` | string | 是 | 初标者 GitHub 用户名 |
| `annotated_at` | date | 是 | 初标日期（YYYY-MM-DD） |
| `last_reviewed_at` | date | 是 | 最后复核日期 |
| `notes` | string | 否 | 标注理由、边界情况说明 |

### 2.3 字段约束

- `query` 长度 3–200 字符；不 trim；保留原始大小写。
- `expected_domains` 必须是 eTLD+1（如 `python.org` 而非 `docs.python.org`）；用 `tldextract` 验证。
- `known_relevant_urls` 必须是完整 URL（含 scheme），且其 eTLD+1 应出现在 `expected_domains` 中——否则该 URL 不参与 Recall 计算，但仍保留作为参考。
- 同一 `id` 不允许重复；`id` 一旦分配不再修改（重命名要走 deprecation 流程，旧 `id` 至少保留一个 benchmark cycle）。

## 3. 子类别定义

| 子类别 | 前缀 | 说明 | 示例 |
|--------|------|------|------|
| `general_en` | `gen_en` | 普通英文网页查询 | `"best coffee shops berlin"` |
| `general_zh` | `gen_zh` | 中文网页查询 | `"北京 咖啡馆 推荐"` |
| `technical_docs` | `tech` | 官方技术文档 | `"python TaskGroup documentation"` |
| `open_source` | `oss` | 开源项目、包、社区 | `"react useEffect cleanup"` |
| `academic` | `acad` | 学术论文 | `"transformer attention mechanism paper"` |
| `news` | `news` | 近期新闻（标注时窗口） | `"2026 EU AI regulation"` |
| `long_tail` | `long` | 长尾、多义、罕见术语 | `"kerfuffle meaning origin"` |

**每个子类别至少 20 条**，少于 20 条的子类别在 benchmark 报告中只做定性分析，不进入聚合指标。

`news` 子类别有特殊性：时效强，`expected_domains` 应选稳定主流媒体（`reuters.com`、`bbc.com`、`nytimes.com`、`theguardian.com` 等），避免具体文章 URL（链接会过期）。

## 4. 标注流程

### 4.1 初标

1. 标注者在 `docs/benchmark/queries.yaml` 追加查询。
2. 为每条查询分配 `id`（按子类别前缀递增，如 `tech_001`、`tech_002`）。
3. 填写所有必填字段；选填字段按需。
4. 至少标注 1 个 `expected_domain`；2–3 个更佳。
5. `notes` 字段说明"为什么这个域名是期望的"——例如"Python 官方文档"、"react 官方文档"、"主流媒体"。

### 4.2 提交前自检

提交 PR 前标注者完成以下自检：

- [ ] `query` 是真实用户可能输入的形式，不是构造的合成查询。
- [ ] `expected_domains` 每个都能解释"为什么这个域名应该出现"。
- [ ] `known_relevant_urls`（如有）的 eTLD+1 在 `expected_domains` 中。
- [ ] `notes` 字段记录了边界判断（例如"Stack Overflow 有讨论但不计入期望"）。
- [ ] 用 `tldextract` 验证过 `expected_domains` 是合法 eTLD+1（不是 `co.uk` 这类误识别）。
- [ ] `id` 在文件中唯一，且未复用已删除的 `id`。

### 4.3 PR 复核要求

PR 描述必须包含：

- 列出新增/修改的 `id`。
- 标注者声明已完成 §4.2 自检。
- 子类别分布更新（如果新增子类别条数）。

复核者（至少 1 人，非标注者本人）验证：

- `expected_domains` 是否真的对应该查询。
- 是否遗漏了更明显的期望域名。
- `notes` 是否足以让第三方理解判断依据。

复核者可以在 PR 中提议调整 `expected_domains`，调整后 `last_reviewed_at` 更新为复核日期。

### 4.4 复核者职责边界

复核者**不需要**：

- 实际跑搜索验证（这是 benchmark 的工作）。
- 验证每个 URL 仍然可达（时效性问题，超出复核范围）。
- 对每条查询都表示完全赞同——有异议时标记 `contested: true` 而不是阻塞 PR。

复核者**需要**：

- 验证标注的逻辑自洽性（解释是否成立）。
- 防止明显错误（例如把 `python.org` 标成"应出现在 react 查询的结果中"）。
- 检查子类别是否合理错配（例如把 `"react useEffect"` 标成 `general_en`）。

## 5. 质量标准

### 5.1 好标注的特征

- `expected_domains` 是查询的**权威来源**（官方文档、官方网站、知名社区、主流媒体）。
- `notes` 解释了**为什么**这个域名是期望的，不只是**是**什么。
- 多个 `expected_domains` 反映查询的多个合法角度（例如 react 查询可以同时期望 `reactjs.org` 和 `stackoverflow.com`）。
- `difficulty` 字段反映查询真实的判断难度，不是标注者的熟悉度。

### 5.2 避免的反模式

- ❌ 把"搜索结果第一个"当成 `expected_domain`——这是循环论证，benchmark 无法发现召回问题。
- ❌ `expected_domains` 列 5 个以上域名——稀释 Recall 指标的判别力，benchmark 报告中所有方案都会接近 1.0。
- ❌ 用时效性强的 URL 作为 `known_relevant_urls`（例如新闻具体文章链接）。
- ❌ 不写 `notes`——复核者无法判断标注依据，后续维护成本高。
- ❌ 构造的合成查询（"test query for python"）——不是真实用户会输入的形式。

### 5.3 难度分级参考

- `easy`：通用知识，权威域名明确（例如 `"python docs"` → `python.org`）。
- `medium`：需要一定领域知识或近期信息（例如 `"react 19 useTransition"`）。
- `hard`：长尾、多义、或权威来源分散（例如 `"occam's razor original latin text"`）。

难度分级不影响指标计算，只用于报告分层分析。如果不确定，默认 `medium`。

## 6. 争议处理

### 6.1 标记争议

当复核者与标注者对 `expected_domains` 有不同意见且无法达成一致时：

1. 把查询标记为 `contested: true`。
2. 在 `notes` 中记录争议点（例如"复核者认为应加入 stackoverflow.com，标注者认为只应保留官方域名"）。
3. 允许合并 PR——争议不阻塞。
4. 后续 benchmark 跑完后，根据数据决定是修改标注还是保留争议。

### 6.2 数据驱动的修订

benchmark 跑完后，根据结果修订：

- 如果某条 `contested: true` 的查询在所有对照方案中 Recall 都很低，可能标注过于严格——提议放宽 `expected_domains`。
- 反之如果所有方案都 Recall=1.0，可能标注过宽——提议收紧。
- 修订争议查询时，更新 `last_reviewed_at`，保留 `contested: true` 直到达成共识。

### 6.3 标注漂移监控

每隔一个 benchmark cycle（例如每个里程碑结束），统计：

- `contested: true` 的查询比例（应 < 15%）。
- 上次 benchmark 后被修改的查询数（应 < 20%）。

超出阈值说明标注质量不稳定，需要复核标注流程本身（例如子类别定义不清、`expected_domains` 标准不明确）。

## 7. Schema 版本

当前 schema 版本：`1`。

### 7.1 兼容策略

- **不升版本号**：新增可选字段、扩充 enum 取值、补文档说明。
- **升版本号**：必填字段调整、字段语义变更、字段重命名、字段删除。

版本号写在 `queries.yaml` 顶层的 `schema_version` 字段。升级版本号时：

1. 在 `docs/benchmark/migrations/` 下写迁移脚本（YAML 到 YAML）。
2. 跑一次迁移，更新 `queries.yaml`。
3. PR 说明迁移影响（哪些字段变了，benchmark 指标是否需要重新计算）。

### 7.2 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 1 | 2026-06-23 | 初版 schema |

## 8. 文件布局

```
docs/
  benchmark_annotation.md    # 本文档（规范）
  benchmark/
    queries.yaml             # 查询集（schema_version: 1）
    migrations/              # schema 升级时的迁移脚本
    reports/                 # benchmark 报告输出（gitignored）
```

`docs/benchmark/queries.yaml` 和 `docs/benchmark/migrations/` 受版本控制；`docs/benchmark/reports/` 不受版本控制（每次跑 benchmark 重新生成）。

## 9. 与 benchmark 脚本的接口

benchmark 脚本（待实现，里程碑四第 10 步）应：

1. 读取 `docs/benchmark/queries.yaml`，按 `schema_version` 选择解析逻辑。
2. 对每条查询执行所有对照方案（§9.4）。
3. 计算指标时：
   - `Recall@K` 用 `known_relevant_urls` 与返回结果的 `normalized_url` 匹配。
   - `Relevant domains@K` 用 `expected_domains` 与返回结果的 `netloc`（eTLD+1）匹配。
   - `contested: true` 的查询在主报告中单独列出，不进入聚合指标。
4. 输出报告到 `docs/benchmark/reports/<timestamp>_<approach>.json`。

脚本读取字段时的容错：

- 缺失可选字段（`known_relevant_urls`、`difficulty`、`notes`）跳过相关计算，不报错。
- 缺失必填字段（`id`、`query`、`expected_domains` 等）报错并跳过该查询，错误计入"标注质量"统计。
- `schema_version` 不匹配时拒绝运行，提示需要迁移。
