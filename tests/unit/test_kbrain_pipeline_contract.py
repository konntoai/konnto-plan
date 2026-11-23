import ast
from pathlib import Path


def test_analysis_entrypoint_accepts_and_forwards_business_context():
    tree = ast.parse(Path("backend/brain.py").read_text(encoding="utf-8"))
    analyze = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "analyze")
    names = {arg.arg for arg in analyze.args.args}
    assert "business_context" in names
    assert any(isinstance(node, ast.Call) and getattr(node.func, "id", "") == "analysis_system"
               and any(keyword.arg == "business_context" for keyword in node.keywords)
               for node in ast.walk(analyze))


def test_analysis_prompt_includes_retrieved_evidence():
    source = Path("backend/brain.py").read_text(encoding="utf-8")
    assert "AUTHORISED BUSINESS EVIDENCE" in source
    assert "{business_context or" in source
