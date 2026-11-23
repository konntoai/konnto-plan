"""Machine-readable K-BRAIN evaluation runner.

Consumes captured, real application traces; it does not fabricate model output or
claim to test a live model. Each JSONL row is one scenario execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_METADATA = ("scenario_id", "model", "prompt_version", "tested_at", "input_context", "output")


def evaluate_record(record: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one captured trace against explicit assertions and action policy."""
    failures = []
    for field in REQUIRED_METADATA:
        if record.get(field) in (None, "", [], {}):
            failures.append(f"missing required trace field: {field}")

    assertions = record.get("assertions") or {}
    if not isinstance(assertions, dict):
        failures.append("assertions must be an object")
        assertions = {}
    output = str(record.get("output") or "").casefold()
    actions = record.get("tool_calls", [])
    if actions is None:
        actions = []
    if not isinstance(actions, list):
        failures.append("tool_calls must be a list")
        actions = []
    malformed_actions = [index for index, call in enumerate(actions) if not isinstance(call, dict) or not isinstance(call.get("name"), str) or not call.get("name").strip()]
    for index in malformed_actions:
        failures.append(f"tool_calls[{index}] must be an object with a non-empty string name")
    actions = [call for call in actions if isinstance(call, dict) and isinstance(call.get("name"), str) and call.get("name").strip()]

    for field in ("must_include", "must_not_include", "allowed_actions", "forbidden_actions", "expected_actions"):
        value = assertions.get(field)
        if value is not None and (not isinstance(value, list) or any(not isinstance(item, str) for item in value)):
            failures.append(f"assertions.{field} must be a list of strings")
            assertions[field] = []

    for phrase in assertions.get("must_include", []):
        if str(phrase).casefold() not in output:
            failures.append(f"output missing required phrase: {phrase}")
    for phrase in assertions.get("must_not_include", []):
        if str(phrase).casefold() in output:
            failures.append(f"output contains forbidden phrase: {phrase}")

    allowed = set(assertions.get("allowed_actions", []))
    forbidden = set(assertions.get("forbidden_actions", []))
    observed = [str(call.get("name", "")) for call in actions if isinstance(call, dict)]
    for name in observed:
        if name in forbidden:
            failures.append(f"forbidden tool/action executed: {name}")
        if "allowed_actions" in assertions and name not in allowed:
            failures.append(f"unexpected tool/action executed: {name}")

    expected = assertions.get("expected_actions")
    if expected is not None and observed != list(expected):
        failures.append(f"tool/action sequence mismatch: expected {expected}, observed {observed}")

    return {
        "scenario_id": record.get("scenario_id"),
        "model": record.get("model"),
        "prompt_version": record.get("prompt_version"),
        "tested_at": record.get("tested_at"),
        "passed": not failures,
        "failures": failures,
        "observed_actions": observed,
    }


def evaluate_file(path: str | Path) -> dict[str, Any]:
    results = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("each JSONL row must be an object")
                result = evaluate_record(record)
            except Exception as exc:
                result = {"scenario_id": None, "passed": False, "failures": [f"line {line_number}: {exc}"]}
            results.append(result)
    passed = sum(1 for result in results if result["passed"])
    return {"total": len(results), "passed": passed, "failed": len(results) - passed, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate captured KONNTO K-BRAIN traces (JSONL).")
    parser.add_argument("trace_file", help="JSONL file containing captured scenario traces")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()
    report = evaluate_file(args.trace_file)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["failed"] == 0 and report["total"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
