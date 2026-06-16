#!/usr/bin/env python
"""AI Repair Agent for scoutlet auto-heal.

Analyzes engine parse failures, calls an OpenAI-compatible LLM to generate
parser fixes, verifies the fix, and optionally commits the result.

Environment variables:
    OPENAI_API_KEY    — API key for the LLM provider
    OPENAI_API_BASE   — Base URL (e.g. https://api.openai.com/v1)
    OPENAI_MODEL      — Model name (default: gpt-4o)

Usage:
    # Repair specific engines from a health report
    python scripts/auto_heal.py --report health-report.json

    # Repair a single engine directly
    python scripts/auto_heal.py --engine bing --failed-html snapshots/bing/failed_20260612.html

    # Dry run (no commit)
    python scripts/auto_heal.py --report health-report.json --dry-run
"""

import argparse
import ast
import json
import os
import re
import sys
import textwrap
import traceback
from datetime import datetime, timezone
from pathlib import Path

ENGINES_DIR = Path(__file__).resolve().parent.parent / "src" / "scoutlet" / "engines"
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_PATTERNS = [
    r"\bexec\s*\(",
    r"\beval\s*\(",
    r"\bsubprocess\b",
    r"\bos\.system\b",
    r"\bos\.popen\b",
    r"\b__import__\s*\(",
    r"\bopen\s*\(.+['\"]w",
]


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _load_engine_source(engine_name: str) -> str | None:
    """Read the current engine .py source code."""
    path = ENGINES_DIR / f"{engine_name}.py"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def _security_check(code: str) -> list[str]:
    """Check generated code for forbidden patterns. Returns list of violations."""
    violations = []
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            violations.append(pattern)
    return violations


def _verify_syntax(code: str) -> tuple[bool, str]:
    """Verify code compiles without syntax errors."""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"


def _extract_response_function(code: str) -> ast.FunctionDef | None:
    """Extract the `response` function AST node from engine code."""
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "response":
            return node
    return None


def _build_repair_prompt(
    engine_name: str,
    old_code: str,
    failed_html: str,
    baseline_html: str | None = None,
    upstream_diff: str | None = None,
) -> str:
    """Build the LLM prompt for parser repair."""
    sections = [
        "你是一个搜索引擎解析代码修复专家。",
        "",
        "## 任务",
        f"引擎 `{engine_name}` 的 `response()` 解析函数失败了，需要你修复。",
        "",
        "## 背景",
        "- 这是一个搜索引擎聚合工具的引擎代码（scoutlet）",
        "- 引擎通过 `request()` 构建请求，`response()` 解析 HTML/JSON 响应",
        "- `response(resp)` 接收一个响应对象（有 `.text` 属性），返回 `list[dict]`",
        "- 每个结果 dict 必须包含 `url` 和 `title`，可选 `content`/`img_src`/`thumbnail_src` 等",
        "",
        "## 当前引擎代码（已失效）",
        "```python",
        old_code,
        "```",
        "",
        "## 失败时的 HTML 响应",
        "```html",
        failed_html[:8000],  # truncate to avoid token limits
        "```",
    ]

    if baseline_html:
        sections += [
            "",
            "## 上一次成功的 HTML（参考对比）",
            "```html",
            baseline_html[:8000],
            "```",
        ]

    if upstream_diff:
        sections += [
            "",
            "## SearXNG 上游最新代码（参考）",
            "```python",
            upstream_diff[:4000],
            "```",
        ]

    sections += [
        "",
        "## 要求",
        "1. 分析 HTML 结构发生了什么变化",
        "2. 更新 `response()` 中的 XPath/正则/解析逻辑以适配新的 HTML 结构",
        "3. **不要改动 `request()` 函数**（请求逻辑不变）",
        "4. 不要改变返回值的字段结构",
        "5. 不要引入新的第三方依赖",
        "6. 不要使用 `exec()`、`eval()`、`subprocess`、`os.system` 等",
        "",
        "## 输出格式",
        "直接输出完整的修改后的 Python 引擎文件内容。",
        "不要用 markdown 代码块包裹，不要加任何解释说明。",
        "只输出纯 Python 代码。",
    ]

    return "\n".join(sections)


def _build_patch_prompt(
    engine_name: str,
    old_code: str,
    error_details: str,
    failed_html: str,
) -> str:
    """Build a follow-up prompt when the first fix attempt failed."""
    return textwrap.dedent(f"""\
        上一次修复尝试失败了，请基于错误信息继续修复。

        引擎: {engine_name}

        错误信息:
        {error_details}

        失败 HTML 片段:
        {failed_html[:4000]}

        当前代码:
        {old_code}

        请输出完整的修复后的 Python 文件，不要用代码块包裹。
    """)


def call_llm(prompt: str, api_key: str, api_base: str, model: str) -> str:
    """Call an OpenAI-compatible chat completion API."""
    import urllib.request
    import urllib.error

    url = f"{api_base.rstrip('/')}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 4096,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM API error {e.code}: {body}") from e


def _extract_code(raw_output: str) -> str:
    """Extract Python code from LLM output, stripping markdown fences if present."""
    text = raw_output.strip()

    # strip markdown code fences
    if text.startswith("```python"):
        text = text[len("```python"):]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def verify_fix(engine_name: str, code: str, test_html: str) -> tuple[bool, str, int]:
    """Verify a generated engine fix against saved test HTML.

    Returns: (passed, error_message, result_count)
    """
    # 1. Syntax check
    ok, err = _verify_syntax(code)
    if not ok:
        return False, err, 0

    # 2. Security check
    violations = _security_check(code)
    if violations:
        return False, f"Forbidden patterns found: {violations}", 0

    # 3. Structural check: must have response() function
    func = _extract_response_function(code)
    if func is None:
        return False, "No response() function found", 0

    # 4. Load module and test
    import importlib.util
    import types

    module_name = f"_test_fix_{engine_name}"
    spec = importlib.util.spec_from_loader(module_name, loader=None)
    module = importlib.util.module_from_spec(spec)

    try:
        exec(compile(code, f"{engine_name}_fix.py", "exec"), module.__dict__)
    except Exception as e:
        return False, f"Module load error: {e}", 0

    if not hasattr(module, "response"):
        return False, "Module has no response() function", 0

    # 5. Run response() with mock
    class MockResponse:
        def __init__(self, text: str):
            self.text = text
            self.status_code = 200
            self.url = "https://example.com/search"
            self.search_params = {}

    try:
        results = module.response(MockResponse(test_html))
    except Exception as e:
        return False, f"response() error: {e}", 0

    if not isinstance(results, list):
        return False, f"response() returned {type(results).__name__}, expected list", 0

    # 6. Validate results
    valid_count = 0
    for i, r in enumerate(results):
        if not isinstance(r, dict):
            return False, f"Result {i} is {type(r).__name__}, expected dict", 0
        if not r.get("url"):
            return False, f"Result {i}: missing url", 0
        if not r.get("title"):
            return False, f"Result {i}: missing title", 0
        valid_count += 1

    if valid_count == 0:
        return False, "No valid results parsed", 0

    return True, f"Extracted {valid_count} valid results", valid_count


def repair_engine(
    engine_name: str,
    failed_html: str,
    baseline_html: str | None = None,
    upstream_code: str | None = None,
    max_attempts: int = 3,
    dry_run: bool = False,
) -> dict:
    """Attempt to repair an engine's parser using LLM.

    Returns a result dict with keys: engine, status, attempts, message, new_code
    """
    api_key = _env("OPENAI_API_KEY")
    api_base = _env("OPENAI_API_BASE", "https://api.openai.com/v1")
    model = _env("OPENAI_MODEL", "gpt-4o")

    if not api_key:
        return {
            "engine": engine_name,
            "status": "error",
            "attempts": 0,
            "message": "OPENAI_API_KEY not set",
            "new_code": None,
        }

    old_code = _load_engine_source(engine_name)
    if not old_code:
        return {
            "engine": engine_name,
            "status": "error",
            "attempts": 0,
            "message": f"Engine source not found: {engine_name}",
            "new_code": None,
        }

    prompt = _build_repair_prompt(engine_name, old_code, failed_html, baseline_html, upstream_code)

    for attempt in range(1, max_attempts + 1):
        print(f"  Attempt {attempt}/{max_attempts}...", file=sys.stderr)

        try:
            raw_output = call_llm(prompt, api_key, api_base, model)
        except Exception as e:
            print(f"  LLM call failed: {e}", file=sys.stderr)
            continue

        new_code = _extract_code(raw_output)

        # Verify
        passed, message, result_count = verify_fix(engine_name, new_code, failed_html)

        if passed:
            # Save fix
            if not dry_run:
                engine_path = ENGINES_DIR / f"{engine_name}.py"
                engine_path.write_text(new_code, encoding="utf-8")

            return {
                "engine": engine_name,
                "status": "fixed",
                "attempts": attempt,
                "message": message,
                "result_count": result_count,
                "new_code": new_code if dry_run else None,
            }

        # Prepare follow-up prompt with error details
        print(f"  Verification failed: {message}", file=sys.stderr)
        prompt = _build_patch_prompt(engine_name, new_code, message, failed_html)

    return {
        "engine": engine_name,
        "status": "failed",
        "attempts": max_attempts,
        "message": f"Could not fix after {max_attempts} attempts",
        "new_code": None,
    }


def process_report(report_path: str, snapshots_dir: str, dry_run: bool = False) -> list[dict]:
    """Process a health report JSON and attempt repairs for parse failures."""
    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    # Find engines with parse-related failures
    repairable = [e for e in report if e.get("status") in ("empty", "parser_error")]

    if not repairable:
        print("No parse failures to repair.", file=sys.stderr)
        return []

    print(f"Found {len(repairable)} engines with parse failures.", file=sys.stderr)

    results = []
    snap_dir = Path(snapshots_dir)
    for entry in repairable:
        engine_name = entry["engine"]
        print(f"\nRepairing {engine_name}...", file=sys.stderr)

        # Load failed HTML from snapshot
        from snapshot import load_baseline, load_latest_failure

        failed_html, failed_path = load_latest_failure(engine_name, snap_dir)
        if not failed_html:
            print(f"  No failure snapshot found for {engine_name}, skipping.", file=sys.stderr)
            results.append({
                "engine": engine_name,
                "status": "skipped",
                "attempts": 0,
                "message": "No failure snapshot available",
                "new_code": None,
            })
            continue

        baseline_html = load_baseline(engine_name, snap_dir)
        result = repair_engine(
            engine_name, failed_html, baseline_html, dry_run=dry_run
        )
        results.append(result)

        status = result["status"]
        print(f"  Result: {status} ({result.get('message', '')})", file=sys.stderr)

    return results


def main():
    parser = argparse.ArgumentParser(description="scoutlet AI auto-heal agent")
    parser.add_argument("--report", help="Path to health report JSON (from health_check.py)")
    parser.add_argument("--engine", help="Repair a single engine by name")
    parser.add_argument("--failed-html", help="Path to failed HTML snapshot (used with --engine)")
    parser.add_argument("--baseline-html", help="Path to baseline HTML (used with --engine)")
    parser.add_argument("--snapshots-dir", default="snapshots", help="Snapshots directory")
    parser.add_argument("--max-attempts", type=int, default=3, help="Max LLM repair attempts per engine")
    parser.add_argument("--dry-run", action="store_true", help="Don't write any files")
    parser.add_argument("--output", "-o", help="Write repair results to JSON file")
    args = parser.parse_args()

    if args.report:
        results = process_report(args.report, args.snapshots_dir, dry_run=args.dry_run)
    elif args.engine:
        failed_html = None
        if args.failed_html:
            failed_html = Path(args.failed_html).read_text(encoding="utf-8")
        else:
            from snapshot import load_baseline, load_latest_failure
            failed_html, _ = load_latest_failure(args.engine, Path(args.snapshots_dir))

        if not failed_html:
            print(f"No failed HTML found for {args.engine}", file=sys.stderr)
            sys.exit(1)

        baseline_html = None
        if args.baseline_html:
            baseline_html = Path(args.baseline_html).read_text(encoding="utf-8")
        else:
            from snapshot import load_baseline
            baseline_html = load_baseline(args.engine, Path(args.snapshots_dir))

        result = repair_engine(
            args.engine, failed_html, baseline_html,
            max_attempts=args.max_attempts, dry_run=args.dry_run,
        )
        results = [result]
    else:
        parser.print_help()
        sys.exit(1)

    # Output
    output = json.dumps(results, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"\nResults written to {args.output}", file=sys.stderr)
    else:
        print(output)

    # Exit code
    all_ok = all(r["status"] in ("fixed", "skipped") for r in results)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
