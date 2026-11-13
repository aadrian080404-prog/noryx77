from __future__ import annotations

import json

from devtools.build_component_registry import build_inventory


def test_inventory_records_domains_dependencies_and_limits(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "core" / "identity.py").write_text("class Principal: pass\n", encoding="utf-8")
    (tmp_path / "core" / "actions.py").write_text("from core.identity import Principal\n", encoding="utf-8")
    (tmp_path / "tests" / "test_identity.py").write_text("def test_principal(): pass\n", encoding="utf-8")

    result = build_inventory(tmp_path)
    assert result["schema_version"] == 1
    assert result["file_count"] == 4
    actions = next(item for item in result["files"] if item["path"] == "core/actions.py")
    assert "core.identity" in actions["internal_imports"]
    assert "B_identity_authorization" in actions["domains"]
    assert result["analysis_limits"]["function_call_graph"] == "not_built"
    json.dumps(result)


def test_inventory_does_not_promote_presence_to_verified(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "feature.py").write_text("def run(): return 1\n", encoding="utf-8")
    result = build_inventory(tmp_path)
    item = next(item for item in result["files"] if item["path"] == "core/feature.py")
    assert item["lifecycle"] == "source_present_not_proof_of_integration"
