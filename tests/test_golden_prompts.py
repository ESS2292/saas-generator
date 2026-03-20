import pytest

from engine.project_builder import build_project_from_manifest
from engine.validator import validate_project_scaffold
from tests.golden_prompts import GOLDEN_PROMPTS


@pytest.mark.parametrize("case", GOLDEN_PROMPTS, ids=[case["name"] for case in GOLDEN_PROMPTS])
def test_golden_prompt_manifest_normalization(case, tmp_path):
    manifest, _saved_files = build_project_from_manifest(
        case["manifest_output"], app_root=str(tmp_path / f"{case['name']}-normalize")
    )

    assert manifest["app_type"] == case["expected"]["app_type"]
    assert manifest["primary_entity"] == case["expected"]["primary_entity"]
    assert [page["name"] for page in manifest["pages"][: len(case["expected"]["page_names"])]] == case["expected"]["page_names"]
    assert any(route["path"] == case["expected"]["route_path"] for route in manifest["api_routes"])
    assert case["expected"]["family_module"] in manifest["family_modules"]
    assert manifest["permissions"]
    assert manifest["layout"]["navigation_style"]


@pytest.mark.parametrize("case", GOLDEN_PROMPTS, ids=[case["name"] for case in GOLDEN_PROMPTS])
def test_golden_prompt_scaffold_generation(case, tmp_path):
    app_root = tmp_path / case["name"]
    manifest, saved_files = build_project_from_manifest(case["manifest_output"], app_root=str(app_root))

    assert "backend/app_core.py" in saved_files
    assert "frontend/src/appShell.jsx" in saved_files
    assert "manifest.json" in saved_files
    assert validate_project_scaffold(str(app_root)) is True

    manifest_path = app_root / "manifest.json"
    assert manifest_path.exists()
    assert case["expected"]["family_module"] in manifest["family_modules"]
