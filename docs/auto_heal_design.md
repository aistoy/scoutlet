# scoutlet Engine Auto-Heal 方案设计

## 概述

当搜索引擎 HTML 结构变化导致解析失败时，AI Agent 自动分析失败原因、重写解析代码、测试验证、提交修复。实现引擎层的自我修复闭环。

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                  Health Monitor                      │
│  (GitHub Actions cron / 本地定时任务)                  │
│                                                      │
│  定时触发 → 逐引擎测试 → 分类失败 → 触发修复           │
└──────────────┬──────────────────────┬───────────────┘
               │                      │
        ┌──────▼──────┐        ┌──────▼──────┐
        │ 解析失败     │        │ 反爬失败     │
        │ HTTP 200    │        │ 403/429/302 │
        │ 结果为空     │        │ CAPTCHA     │
        └──────┬──────┘        └──────┬──────┘
               │                      │
        ┌──────▼──────────┐    ┌──────▼──────┐
        │ AI Repair Agent │    │ CDP Fallback │
        │ (Claude API)    │    │ (已有机制)   │
        └──────┬──────────┘    └─────────────┘
               │
    ┌──────────▼──────────┐
    │ 1. 保存失败 HTML     │
    │ 2. 分析结构变化      │
    │ 3. 重写解析代码      │
    │ 4. 自动测试验证      │
    │ 5. 通过 → 提交       │
    │ 6. 不通过 → 重试/人工 │
    └──────────┬──────────┘
               │
        ┌──────▼──────┐
        │ Git Commit  │
        │ / PR        │
        └─────────────┘
```

## 模块设计

### 1. Health Monitor

**职责：** 定时检测所有引擎健康状态，分类失败类型。

**输入：** 引擎列表 + 测试查询词
**输出：** 健康报告 JSON + HTML 快照

**测试策略：**

每个引擎使用固定的测试查询词（确保正常情况下一定能返回结果）：

| 引擎 | 测试查询 | 预期最小结果数 |
|------|---------|--------------|
| google | `"python tutorial"` | 5 |
| bing | `"python tutorial"` | 5 |
| duckduckgo | `"python tutorial"` | 5 |
| brave | `"python tutorial"` | 5 |
| github | `"requests http"` | 3 |
| gitlab | `"gitlab"` | 3 |
| baidu | `"Python"` | 5 |
| sogou | `"Python"` | 5 |
| bilibili | `"Python"` | 3 |

**失败分类逻辑：**

```python
def classify_failure(engine_name, resp, results, error):
    if error and isinstance(error, (SearchEngineCaptchaException,
                                     SearchEngineAccessDeniedException)):
        return FailureType.ANTI_BOT

    if error and isinstance(error, SearchEngineTooManyRequestsException):
        return FailureType.RATE_LIMIT

    if resp.status_code in (403, 429, 503):
        return FailureType.ANTI_BOT

    if resp.status_code >= 400:
        return FailureType.HTTP_ERROR

    if resp.status_code == 200 and len(results) == 0:
        return FailureType.PARSE_FAILURE  # ← 触发 AI 修复

    return FailureType.UNKNOWN
```

**健康报告格式：**

```json
{
  "timestamp": "2026-05-16T10:00:00Z",
  "results": {
    "google": {
      "status": "healthy",
      "result_count": 10,
      "response_time_ms": 320
    },
    "bing": {
      "status": "parse_failure",
      "result_count": 0,
      "response_time_ms": 280,
      "html_snapshot": "snapshots/bing_2026-05-16.html",
      "error": "EmptyResultError"
    },
    "duckduckgo": {
      "status": "anti_bot",
      "result_count": 0,
      "response_time_ms": 150,
      "error": "SearchEngineCaptchaException"
    }
  }
}
```

### 2. HTML Snapshot Manager

**职责：** 保存成功和失败时的 HTML 响应，供 AI 分析和回归测试使用。

**存储结构：**

```
snapshots/
├── google/
│   ├── baseline.html          # 上一次成功的 HTML（参考）
│   └── failed_2026-05-16.html # 失败时的 HTML
├── bing/
│   ├── baseline.html
│   └── failed_2026-05-16.html
└── ...
```

**用途：**
- `baseline.html` — 给 AI 对比 "之前长什么样"
- `failed_*.html` — 给 AI 分析 "现在长什么样"
- 成功时自动更新 baseline

### 3. AI Repair Agent

**职责：** 分析失败的 HTML，重写 engine 解析代码，测试验证。

**输入：**
- 失败的 engine 名称
- 旧 engine 代码（当前 `.py` 文件）
- 失败时的 HTML 快照
- 上一次成功的 HTML baseline（用于对比）
- SearXNG 上游最新 engine 代码（可选，作为参考）

**输出：**
- 新的 engine `.py` 文件
- 修复说明（commit message）

**Prompt 设计：**

```
你是一个搜索引擎解析代码修复专家。

## 任务
引擎 {engine_name} 的解析代码失败了，需要你修复。

## 背景
- 这是一个搜索引擎聚合工具的引擎代码
- 引擎通过 request() 构建请求，response() 解析 HTML 响应
- response() 应返回包含 url/title/content 的字典列表

## 旧代码（已失效）
```python
{old_code}
```

## 失败时的 HTML 响应
```html
{failed_html}
```

## 上一次成功的 HTML（参考对比）
```html
{baseline_html}
```

## 要求
1. 分析 HTML 结构发生了什么变化
2. 更新 response() 中的 XPath/正则/解析逻辑以适配新的 HTML 结构
3. 不要改动 request() 函数（请求逻辑不变）
4. 不要改变返回值的字段结构
5. 输出完整的修改后的 engine 文件

## 输出格式
直接输出完整的 Python 文件内容，不要用代码块包裹。
```

**修复流程：**

```python
def auto_repair(engine_name, max_retries=3):
    # 1. 收集上下文
    old_code = read_engine_file(engine_name)
    failed_html = load_snapshot(engine_name, "failed")
    baseline_html = load_snapshot(engine_name, "baseline")
    upstream_code = fetch_searxng_upstream(engine_name)  # 可选

    for attempt in range(max_retries):
        # 2. 调用 AI 生成修复代码
        new_code = call_claude_api(
            prompt=build_repair_prompt(
                engine_name, old_code, failed_html, baseline_html, upstream_code
            )
        )

        # 3. 验证修复
        test_result = test_engine_code(engine_name, new_code, failed_html)

        if test_result.passed:
            # 4. 保存 + 提交
            save_engine_file(engine_name, new_code)
            commit_fix(engine_name, test_result.summary)
            return RepairResult(status="fixed", attempts=attempt + 1)

        # 5. 失败则把错误信息加入下一轮 prompt
        old_code = new_code  # 基于新代码继续修
        error_context = test_result.error_details

    return RepairResult(status="failed", attempts=max_retries)
```

### 4. Auto-Tester

**职责：** 验证 AI 生成的新引擎代码是否正确。

**验证步骤：**

```python
def test_engine_code(engine_name, code, test_html):
    # 1. 语法检查
    try:
        compile(code, f"{engine_name}.py", "exec")
    except SyntaxError as e:
        return TestResult(passed=False, error=f"SyntaxError: {e}")

    # 2. 沙箱加载
    module = load_module_from_string(code)
    if not hasattr(module, 'response'):
        return TestResult(passed=False, error="Missing response() function")

    # 3. 用保存的 HTML 执行解析
    mock_resp = MockResponse(text=test_html, status_code=200)
    try:
        results = module.response(mock_resp)
    except Exception as e:
        return TestResult(passed=False, error=f"ResponseError: {e}")

    # 4. 结果验证
    if not results or len(results) == 0:
        return TestResult(passed=False, error="Empty results")

    for i, r in enumerate(results):
        if not r.get('url'):
            return TestResult(passed=False, error=f"Result {i}: missing url")
        if not r.get('title'):
            return TestResult(passed=False, error=f"Result {i}: missing title")

    return TestResult(
        passed=True,
        result_count=len(results),
        summary=f"Extracted {len(results)} valid results"
    )
```

**验证规则：**

| 检查项 | 条件 |
|--------|------|
| 语法 | 代码能 compile |
| 结构 | 有 `response()` 函数 |
| 执行 | `response(mock_resp)` 不抛异常 |
| 结果数 | ≥ 1 条有效结果 |
| URL | 每条结果有非空 url，且是合法 URL |
| 标题 | 每条结果有非空 title |
| 无安全风险 | 禁止 `exec()`、`eval()`、`subprocess`、`os.system` 等 |

### 5. Git Commit & 通知

**提交策略：**

- 修复后直接提交到 `auto-fix/{engine_name}` 分支
- 生成 PR 到 master，包含修复说明和测试结果
- 可选：合并策略（自动合并 / 需人工 review）

**提交信息格式：**

```
[auto-fix] {engine_name}: update parsing for HTML structure change

- Failed: {failure_type}
- Baseline date: {baseline_date}
- Fix: {ai_summary_of_change}
- Test: {result_count} results extracted from saved HTML
- Attempts: {attempt_count}
```

**通知：**

修复完成后发送通知（可配置）：

- GitHub Issue（自动创建/关闭）
- Webhook（飞书/钉钉/Slack）
- 邮件

## 运行环境

### 方案 A：GitHub Actions（推荐）

```yaml
# .github/workflows/engine_health.yml
name: Engine Health Check
on:
  schedule:
    - cron: '0 */6 * * *'  # 每 6 小时
  workflow_dispatch:         # 手动触发

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install -e .

      # 健康检查
      - run: python scripts/health_check.py --output report.json

      # 保存快照
      - uses: actions/upload-artifact@v4
        with:
          name: snapshots
          path: snapshots/

      # 自动修复（仅对 parse_failure 的引擎）
      - run: python scripts/auto_heal.py --report report.json
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      # 提交修复
      - run: |
          git config user.name "auto-heal-bot"
          git config user.email "bot@scoutlet.dev"
          python scripts/commit_fixes.py
```

### 方案 B：本地定时运行

```bash
# crontab
0 */6 * * * cd /path/to/scoutlet && python scripts/health_check.py --auto-heal
```

## SearXNG 上游同步（可选增强）

作为 AI 修复的补充，定期检查 SearXNG 上游是否有对应引擎的更新：

```python
def check_searxng_upstream(engine_name):
    """检查 SearXNG 上游是否有该引擎的最近 commit"""
    # 1. 获取 SearXNG 仓库该引擎文件的最新 commit
    # 2. 与本地版本对比
    # 3. 如果上游有更新，自动 port 到 scoutlet 格式
    #    （这也是 AI 可以做的任务）
```

## 配置

```yaml
# auto_heal.yaml
schedule: "0 */6 * * *"     # 检查频率
max_repair_attempts: 3       # AI 修复最大重试次数
ai_model: "claude-sonnet-4-20250514"  # 使用的模型

engines:
  google:
    test_query: "python tutorial"
    min_results: 5
    proxy: ""                 # 可选代理
  bing:
    test_query: "python tutorial"
    min_results: 5
  github:
    test_query: "requests http"
    min_results: 3

notification:
  type: "webhook"             # webhook / issue / email
  webhook_url: ""
```

## 成本估算

| 项目 | 预估 |
|------|------|
| Claude API（每次修复） | ~2K input + ~1K output tokens ≈ $0.02 |
| GitHub Actions（每月） | 免费额度内（2000 min/month） |
| 代理（如需） | 按实际使用 |

假设每月 2-3 次引擎 HTML 结构变化，每次修复重试 2 次：约 $0.1-0.2/月。

## 实施计划

### Phase 1：监控基础设施
- [ ] `scripts/health_check.py` — 健康检查脚本
- [ ] `scripts/snapshot.py` — HTML 快照管理
- [ ] `.github/workflows/engine_health.yml` — GitHub Actions workflow

### Phase 2：AI 自动修复
- [ ] `scripts/auto_heal.py` — AI 修复主逻辑
- [ ] `scripts/test_fix.py` — 自动测试验证
- [ ] Prompt 模板设计和调优

### Phase 3：分发与通知
- [ ] Git commit / PR 自动创建
- [ ] Webhook 通知
- [ ] SearXNG 上游同步检查
