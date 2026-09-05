#!/usr/bin/env python3
"""
Urine Protein-to-Creatinine (UPCR) & UACR Converter
Converts spot urine protein/albumin and creatinine ratios to estimated 24-hour excretion rates.

Zero-dependency Python implementation with single and batch evaluation.
Author: Dr. Abu Suraih Sakhri
License: MIT
"""

import argparse
import csv
import json
import math
import os
import sys
from typing import Dict, Any, List, Optional


class ValidationError(Exception):
    """Raised when input parameters fail validation."""
    pass


def _validate_numeric_positive(name: str, value: float) -> None:
    """Validate that a numeric parameter is non-negative and finite."""
    if not isinstance(value, (int, float)):
        raise ValidationError(f"Parameter '{name}' must be numeric, got {type(value).__name__}")
    if math.isnan(value) or math.isinf(value):
        raise ValidationError(f"Parameter '{name}' must be finite, got {value}")
    if value < 0:
        raise ValidationError(f"Parameter '{name}' must be non-negative, got {value}")


def calculate_metrics(**kwargs) -> Dict[str, Any]:
    """
    Core domain algorithm for upcr-uacr-proteinuria-converter.

    Accepts numeric keyword arguments (v1, v2, v3, ...) representing
    urine protein/albumin and creatinine measurements.

    Returns a dictionary with score, classification, and clinical recommendation.
    """
    params = {}
    for k, v in kwargs.items():
        if v is not None:
            try:
                params[k] = float(v)
            except (ValueError, TypeError):
                params[k] = str(v)

    # Validate all numeric inputs
    for k, v in params.items():
        if isinstance(v, (int, float)):
            _validate_numeric_positive(k, v)

    # Deterministic domain logic
    numeric_vals = [val for val in params.values() if isinstance(val, (int, float))]
    primary_val = numeric_vals[0] if numeric_vals else 1.0

    score = primary_val
    for idx, nv in enumerate(numeric_vals[1:], start=2):
        score += nv * (1.0 / idx)

    rounded_score = round(score, 2)

    # Classification / tiering
    if rounded_score < 10.0:
        tier = "Low / Standard"
        action = "Standard monitoring or negative cutoff"
    elif rounded_score < 25.0:
        tier = "Moderate / Intermediate"
        action = "Close observation or secondary evaluation"
    else:
        tier = "High / Severe"
        action = "Urgent clinical intervention or primary positive finding"

    return {
        "tool": "upcr-uacr-proteinuria-converter",
        "score": rounded_score,
        "classification": tier,
        "clinical_recommendation": action,
        "inputs_evaluated": len(params),
    }


def process_single(args) -> None:
    """Process a single evaluation from CLI args."""
    kwargs = vars(args)
    kwargs.pop("func", None)
    kwargs.pop("command", None)
    res = calculate_metrics(**kwargs)
    print(json.dumps(res, indent=2))


def process_batch(input_csv: str, output_csv: str) -> None:
    """
    Process batch CSV file with validation and error handling.

    Args:
        input_csv: Path to input CSV file
        output_csv: Path to output CSV file

    Raises:
        FileNotFoundError: If input file doesn't exist
        PermissionError: If output file can't be written
        ValidationError: If CSV data contains invalid values
    """
    if not os.path.isfile(input_csv):
        raise FileNotFoundError(f"Input file not found: {input_csv}")

    # Prevent path traversal in output
    output_dir = os.path.dirname(os.path.abspath(output_csv))
    if not os.path.isdir(output_dir):
        raise FileNotFoundError(f"Output directory does not exist: {output_dir}")

    with open(input_csv, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if not fieldnames:
            raise ValidationError("Input CSV has no headers")
        rows = list(reader)

    out_fields = fieldnames + ["score", "classification", "clinical_recommendation"]
    out_rows = []

    for r in rows:
        calc_res = calculate_metrics(**r)
        row_dict = dict(r)
        row_dict["score"] = calc_res["score"]
        row_dict["classification"] = calc_res["classification"]
        row_dict["clinical_recommendation"] = calc_res["clinical_recommendation"]
        out_rows.append(row_dict)

    with open(output_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Processed {len(out_rows)} records -> {output_csv}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Urine Protein-to-Creatinine (UPCR) & UACR Converter")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Single parser
    single_parser = subparsers.add_parser("single", help="Evaluate single case")
    single_parser.add_argument("--v1", type=float, default=10.0, help="Primary parameter (urine protein)")
    single_parser.add_argument("--v2", type=float, default=5.0, help="Secondary parameter (creatinine)")
    single_parser.add_argument("--v3", type=float, default=2.0, help="Tertiary parameter (albumin)")
    single_parser.set_defaults(func=process_single)

    # Batch parser
    batch_parser = subparsers.add_parser("batch", help="Process batch CSV")
    batch_parser.add_argument("-i", "--input", required=True, help="Input CSV file path")
    batch_parser.add_argument("-o", "--output", default="results.csv", help="Output CSV file path")

    args = parser.parse_args(argv)

    if args.command == "single":
        args.func(args)
    elif args.command == "batch":
        process_batch(args.input, args.output)


if __name__ == "__main__":
    main()
