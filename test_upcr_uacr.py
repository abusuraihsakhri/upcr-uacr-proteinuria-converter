import pytest
import math
from upcr_uacr import calculate_metrics, process_batch, ValidationError


def test_upcr_uacr_single():
    res = calculate_metrics(v1=12.0, v2=4.0)
    assert "score" in res
    assert "classification" in res
    assert res["score"] > 0


def test_upcr_uacr_batch(tmp_path):
    csv_in = tmp_path / "in.csv"
    csv_out = tmp_path / "out.csv"
    csv_in.write_text("Patient,v1,v2\nPat_001,15.0,3.0\nPat_002,5.0,1.0\n", encoding="utf-8")

    process_batch(str(csv_in), str(csv_out))
    assert csv_out.exists()
    content = csv_out.read_text(encoding="utf-8")
    assert "Pat_001" in content
    assert "score" in content


def test_calculate_metrics_classification_low():
    """Test classification for low scores (< 10.0)."""
    res = calculate_metrics(v1=5.0, v2=2.0)
    assert res["classification"] == "Low / Standard"
    assert "Standard monitoring" in res["clinical_recommendation"]


def test_calculate_metrics_classification_moderate():
    """Test classification for moderate scores (10.0 - 24.9)."""
    res = calculate_metrics(v1=15.0, v2=5.0)
    assert res["classification"] == "Moderate / Intermediate"
    assert "Close observation" in res["clinical_recommendation"]


def test_calculate_metrics_classification_high():
    """Test classification for high scores (>= 25.0)."""
    res = calculate_metrics(v1=30.0, v2=10.0)
    assert res["classification"] == "High / Severe"
    assert "Urgent clinical intervention" in res["clinical_recommendation"]


def test_calculate_metrics_validation_negative():
    """Test that negative values raise ValidationError."""
    with pytest.raises(ValidationError, match="non-negative"):
        calculate_metrics(v1=-5.0)


def test_calculate_metrics_validation_nan():
    """Test that NaN values raise ValidationError."""
    with pytest.raises(ValidationError, match="finite"):
        calculate_metrics(v1=float("nan"))


def test_calculate_metrics_validation_inf():
    """Test that infinite values raise ValidationError."""
    with pytest.raises(ValidationError, match="finite"):
        calculate_metrics(v1=float("inf"))


def test_calculate_metrics_string_input():
    """Test that string inputs are handled gracefully."""
    res = calculate_metrics(v1="abc", v2=5.0)
    assert res["score"] > 0
    assert res["inputs_evaluated"] == 2


def test_calculate_metrics_empty():
    """Test calculate_metrics with no arguments."""
    res = calculate_metrics()
    assert res["score"] == 1.0
    assert res["classification"] == "Low / Standard"


def test_process_batch_file_not_found(tmp_path):
    """Test that FileNotFoundError is raised for missing input file."""
    with pytest.raises(FileNotFoundError):
        process_batch(str(tmp_path / "nonexistent.csv"), str(tmp_path / "out.csv"))


def test_process_batch_invalid_output_dir(tmp_path):
    """Test that FileNotFoundError is raised for invalid output directory."""
    csv_in = tmp_path / "in.csv"
    csv_in.write_text("v1,v2\n5.0,2.0\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        process_batch(str(csv_in), "/nonexistent/dir/out.csv")


def test_process_batch_empty_csv(tmp_path):
    """Test that ValidationError is raised for CSV with no headers."""
    csv_in = tmp_path / "in.csv"
    csv_out = tmp_path / "out.csv"
    csv_in.write_text("", encoding="utf-8")
    with pytest.raises(ValidationError, match="no headers"):
        process_batch(str(csv_in), str(csv_out))
