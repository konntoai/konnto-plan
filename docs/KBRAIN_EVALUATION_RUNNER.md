# Running K-BRAIN evaluations

The acceptance scenarios are defined in `docs/KBRAIN_EVALUATION_SET.md`.
The runner evaluates captured application traces; it does not call a model,
fabricate an output, or substitute for live role/tenant integration testing.

## Trace format

One JSON object per line (JSONL):

```json
{
  "scenario_id": "KB-031",
  "model": "exact-model-id-and-version",
  "prompt_version": "git-sha-or-prompt-version",
  "tested_at": "2026-11-24T00:00:00Z",
  "input_context": {"role": "employee", "user_message": "Captured test input"},
  "output": "Exact assistant response",
  "tool_calls": [],
  "assertions": {
    "must_include": ["owner approval"],
    "must_not_include": ["payment approved"],
    "allowed_actions": [],
    "forbidden_actions": ["approve_payment"],
    "expected_actions": []
  }
}
```

Record the actual model, prompt version, input context, assistant output and
observed backend tool/action calls. Never infer tool execution from assistant
prose. Use only synthetic test data; redact credentials and personal data.

## Run

From the repository root:

```bash
python -m backend.kbrain_eval path/to/captured-traces.jsonl --output eval-report.json
```

Exit code is non-zero when the file is empty or any trace fails. A passing
offline report is evidence only for the captured cases and assertions; it is
not a release approval. The release gate still requires role variants,
negative permission cases, live integration checks and inspection of actual
tool outcomes.
