"""Reference and edge-case tests for urine protein/albumin ratios."""
import csv
import math
import pytest

from upcr_uacr import calculate_metrics, convert_ratio, process_batch, ValidationError


def test_calculated_ratios_and_units():
    result = calculate_metrics(protein_mg_dl=20, albumin_mg_dl=5, creatinine_mg_dl=100)
    assert result["upcr_mg_g"] == pytest.approx(200)
    assert result["uacr_mg_g"] == pytest.approx(50)
    assert result["upcr_mg_mmol"] == pytest.approx(22.624)
    assert result["uacr_mg_mmol"] == pytest.approx(5.656)
    assert result["albumin_fraction_percent"] == pytest.approx(25)
    assert result["albuminuria_category"].startswith("A2")


@pytest.mark.parametrize("input_value,expected", [(0, 0), (29.999, 29.999), (30, 30), (300, 300)])
def test_ratio_round_trip(input_value, expected):
    mmol = convert_ratio(input_value)
    assert convert_ratio(mmol, "mg/mmol", "mg/g") == pytest.approx(expected)


@pytest.mark.parametrize("value,category", [
    (0, "A1"), (29.999, "A1"), (30, "A2"), (299.999, "A2"), (300, "A3")
])
def test_albuminuria_unrounded_boundaries(value, category):
    assert calculate_metrics(uacr_mg_g=value)["albuminuria_category"].startswith(category)


def test_upcr_only_is_not_uacr():
    result = calculate_metrics(upcr_mg_g=280)
    assert result["uacr_mg_g"] is None
    assert result["albuminuria_category"] is None
    assert result["estimated_albumin_mg_day"] is None


def test_daily_excretion_requires_explicit_creatinine():
    assert calculate_metrics(upcr_mg_g=100)["estimated_protein_mg_day"] is None
    r = calculate_metrics(upcr_mg_g=100, uacr_mg_g=40, creatinine_g_day=1.2)
    assert r["estimated_protein_mg_day"] == pytest.approx(120)
    assert r["estimated_albumin_mg_day"] == pytest.approx(48)
    assert r["warnings"]


def test_assay_discordance_is_flagged_not_silently_fixed():
    r = calculate_metrics(upcr_mg_g=50, uacr_mg_g=60)
    assert r["warnings"]
    assert r["albumin_fraction_percent"] == pytest.approx(120)


@pytest.mark.parametrize("kwargs", [
    {}, {"protein_mg_dl": 10},
    {"protein_mg_dl": 10, "creatinine_mg_dl": 0},
    {"protein_mg_dl": -1, "creatinine_mg_dl": 10},
    {"uacr_mg_g": float("nan")}, {"upcr_mg_g": float("inf")},
    {"uacr_mg_g": "not a number"}, {"uacr_mg_g": True},
    {"uacr_mg_g": 20, "albumin_mg_dl": 2, "creatinine_mg_dl": 100},
    {"uacr_mg_g": 20, "creatinine_g_day": 0},
])
def test_invalid_inputs(kwargs):
    with pytest.raises(ValidationError):
        calculate_metrics(**kwargs)


def test_batch_and_metadata(tmp_path):
    src, dst = tmp_path / "values.csv", tmp_path / "out.csv"
    src.write_text("sample_id,protein_mg_dl,albumin_mg_dl,creatinine_mg_dl\n"
                   "A,20,5,100\nB,10,0,200\n", encoding="utf-8")
    assert process_batch(src, dst) == 2
    with dst.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]["sample_id"] == "A"
    assert float(rows[0]["uacr_mg_g"]) == pytest.approx(50)
    assert float(rows[1]["upcr_mg_g"]) == pytest.approx(50)


def test_batch_invalid_row_does_not_create_output(tmp_path):
    src, dst = tmp_path / "values.csv", tmp_path / "out.csv"
    src.write_text("protein_mg_dl,creatinine_mg_dl\n20,100\n-2,100\n")
    with pytest.raises(ValidationError, match="Row 3"):
        process_batch(src, dst)
    assert not dst.exists()


def test_csv_formula_is_neutralized(tmp_path):
    src, dst = tmp_path / "values.csv", tmp_path / "out.csv"
    src.write_text("sample_id,uacr_mg_g\n=HYPERLINK(1),30\n")
    process_batch(src, dst)
    with dst.open(newline="", encoding="utf-8") as f:
        assert next(csv.DictReader(f))["sample_id"].startswith("'=")


def test_batch_missing_and_bad_headers(tmp_path):
    src = tmp_path / "in.csv"
    with pytest.raises(FileNotFoundError):
        process_batch(src, tmp_path / "out.csv")
    src.write_text("uacr_mg_g,uacr_mg_g\n10,20\n")
    with pytest.raises(ValidationError, match="Duplicate"):
        process_batch(src, tmp_path / "out.csv")
