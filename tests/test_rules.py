import json
import subprocess
import sys
from pathlib import Path

import pytest

from game_asset_validator import validate
from game_asset_validator.rules import check_name

GOOD = {
    "name": "SM_WoodenCrate", "kind": "static_mesh", "tri_count": 1240, "has_uv": True,
    "materials": 1, "scale": [1, 1, 1], "dimensions": [1.0, 1.0, 1.0],
    "textures": [{"name": "T_WoodenCrate_D", "width": 1024, "height": 1024}],
}


def codes(report):
    return {i.code for i in report.issues}


def test_valid_asset_passes():
    r = validate(GOOD, "pc")
    assert r.ok and not r.issues


@pytest.mark.parametrize("name,kind,code", [
    ("WoodenCrate", "static_mesh", "NAME_PREFIX"),
    ("SM_wooden crate", "static_mesh", "NAME_FORMAT"),
    ("SM_Crate", "prop", "NAME_KIND"),
])
def test_naming_errors(name, kind, code):
    assert code in {i.code for i in check_name(name, kind)}


def test_triangle_budget_depends_on_profile():
    asset = {**GOOD, "tri_count": 20_000}
    assert validate(asset, "pc").ok
    assert "TRI_BUDGET" in codes(validate(asset, "mobile"))


def test_near_budget_is_only_a_warning():
    r = validate({**GOOD, "tri_count": 25_000}, "pc")
    assert r.ok and "TRI_NEAR_BUDGET" in codes(r)


def test_missing_uv_and_unapplied_scale_are_errors():
    r = validate({**GOOD, "has_uv": False, "scale": [2, 1, 1]}, "pc")
    assert {"UV_MISSING", "SCALE_NOT_APPLIED"} <= codes(r) and not r.ok


def test_texture_rules():
    bad = {**GOOD, "textures": [{"name": "T_Crate_D", "width": 1000, "height": 1024},
                                 {"name": "T_Crate_N", "width": 4096, "height": 4096}]}
    r = validate(bad, "pc")
    assert {"TEXTURE_POW2", "TEXTURE_SIZE"} <= codes(r)


def test_huge_dimension_warns_wrong_units():
    r = validate({**GOOD, "dimensions": [250.0, 1, 1]}, "pc")
    assert r.ok and "DIMENSION_HUGE" in codes(r)


def test_unknown_profile_raises():
    with pytest.raises(ValueError):
        validate(GOOD, "console")


def test_cli_exit_codes(tmp_path):
    good, bad = tmp_path / "good.json", tmp_path / "bad.json"
    good.write_text(json.dumps(GOOD), encoding="utf-8")
    bad.write_text(json.dumps({**GOOD, "has_uv": False}), encoding="utf-8")
    run = lambda f: subprocess.run([sys.executable, "-m", "game_asset_validator", str(f)],
                                   capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    assert run(good).returncode == 0
    res = run(bad)
    assert res.returncode == 1 and "UV_MISSING" in res.stdout
