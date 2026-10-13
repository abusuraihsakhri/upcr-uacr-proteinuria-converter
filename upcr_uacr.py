#!/usr/bin/env python3
"""Dimensionally explicit urine protein/albumin-to-creatinine ratio calculations.

Spot ratios use matched urine measurements. The 24-hour outputs are only
estimates requiring a separately supplied daily creatinine excretion.
"""
import argparse
import csv
import json
import math
from pathlib import Path

CREATININE_G_PER_MMOL = 0.11312
INPUT_FIELDS = (
    "protein_mg_dl", "albumin_mg_dl", "creatinine_mg_dl",
    "upcr_mg_g", "uacr_mg_g", "creatinine_g_day",
)
OUTPUT_FIELDS = (
    "upcr_mg_g", "upcr_mg_mmol", "uacr_mg_g", "uacr_mg_mmol",
    "albuminuria_category", "albumin_fraction_percent",
    "estimated_protein_mg_day", "estimated_albumin_mg_day", "warnings",
)


class ValidationError(ValueError):
    """Invalid or insufficient urine measurement."""


def _number(name, value, *, allow_zero=True):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValidationError(f"{name} must be a finite number")
    try:
        num = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be a finite number") from exc
    if not math.isfinite(num) or num < 0 or (not allow_zero and num == 0):
        raise ValidationError(f"{name} must be finite and {'non-negative' if allow_zero else 'positive'}")
    return num


def convert_ratio(value, from_unit="mg/g", to_unit="mg/mmol"):
    """Convert a protein or albumin mass/creatinine mass ratio to molar units."""
    value = _number("ratio", value)
    if value is None:
        raise ValidationError("ratio is required")
    units = {"mg/g", "mg/mmol"}
    if from_unit not in units or to_unit not in units:
        raise ValidationError("Units must be 'mg/g' or 'mg/mmol'")
    if from_unit == to_unit:
        return value
    if from_unit == "mg/g":
        return value * CREATININE_G_PER_MMOL
    return value / CREATININE_G_PER_MMOL


def calculate_metrics(
    *, protein_mg_dl=None, albumin_mg_dl=None, creatinine_mg_dl=None,
    upcr_mg_g=None, uacr_mg_g=None, creatinine_g_day=None,
):
    """Calculate UPCR and/or UACR from spot urine measurements or given ratios.

    Protein and albumin concentrations must be mg/dL, and matched urine
    creatinine must be mg/dL. Ratios are in mg/g creatinine. No UPCR-to-UACR
    inference is performed because albumin is only part of total protein.
    """
    supplied = dict(
        protein_mg_dl=protein_mg_dl, albumin_mg_dl=albumin_mg_dl,
        creatinine_mg_dl=creatinine_mg_dl, upcr_mg_g=upcr_mg_g,
        uacr_mg_g=uacr_mg_g, creatinine_g_day=creatinine_g_day,
    )
    values = {
        key: _number(key, val, allow_zero=key != "creatinine_g_day")
        for key, val in supplied.items()
    }
    protein = values["protein_mg_dl"]
    albumin = values["albumin_mg_dl"]
    creatinine = values["creatinine_mg_dl"]
    upcr = values["upcr_mg_g"]
    uacr = values["uacr_mg_g"]
    daily = values["creatinine_g_day"]

    if protein is not None and upcr is not None:
        raise ValidationError("Supply either protein_mg_dl or upcr_mg_g, not both")
    if albumin is not None and uacr is not None:
        raise ValidationError("Supply either albumin_mg_dl or uacr_mg_g, not both")
    if protein is None and albumin is None and upcr is None and uacr is None:
        raise ValidationError("Provide a urine protein or albumin measurement or a measured ratio")
    if (protein is not None or albumin is not None) and creatinine is None:
        raise ValidationError("creatinine_mg_dl is required for urine concentrations")
    if creatinine == 0 and (protein is not None or albumin is not None):
        raise ValidationError("creatinine_mg_dl must be positive to calculate ratios")

    if protein is not None:
        upcr = protein / creatinine * 1000.0
    if albumin is not None:
        uacr = albumin / creatinine * 1000.0

    warnings = []
    fraction = None
    if upcr is not None and uacr is not None:
        if upcr > 0:
            fraction = uacr / upcr * 100
        if uacr > upcr + max(1e-9, upcr * 1e-10):
            warnings.append("UACR exceeds UPCR; check specimen comparability, units and assays.")
        elif upcr == 0 and uacr == 0:
            fraction = None

    category = None
    if uacr is not None:
        if uacr < 30:
            category = "A1 — normal to mildly increased"
        elif uacr < 300:
            category = "A2 — moderately increased"
        else:
            category = "A3 — severely increased"

    if daily is not None:
        warnings.append("24-hour excretion is an estimate based on the supplied daily creatinine excretion, not a measured 24-hour collection.")

    return {
        "upcr_mg_g": upcr,
        "upcr_mg_mmol": None if upcr is None else convert_ratio(upcr),
        "uacr_mg_g": uacr,
        "uacr_mg_mmol": None if uacr is None else convert_ratio(uacr),
        "albuminuria_category": category,
        "albumin_fraction_percent": fraction,
        "estimated_protein_mg_day": None if upcr is None or daily is None else upcr * daily,
        "estimated_albumin_mg_day": None if uacr is None or daily is None else uacr * daily,
        "warnings": warnings,
    }


def process_batch(input_csv, output_csv):
    """Process a CSV with named columns; preserve extra non-calculation columns."""
    input_path = Path(input_csv)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_csv}")
    output_path = Path(output_csv)
    if not output_path.parent.is_dir():
        raise FileNotFoundError(f"Output directory does not exist: {output_path.parent}")

    with input_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if not fields:
            raise ValidationError("Input CSV has no headers")
        if len(fields) != len(set(fields)):
            raise ValidationError("Duplicate CSV headers are not allowed")
        if not set(fields).intersection(INPUT_FIELDS[:-1]):
            raise ValidationError("CSV requires a protein/albumin measurement or UPCR/UACR field")
        rows = []
        for index, row in enumerate(reader, start=2):
            if None in row:
                raise ValidationError(f"Row {index}: more values than header columns")
            try:
                result = calculate_metrics(**{k: row.get(k) for k in INPUT_FIELDS if k in fields})
            except ValidationError as exc:
                raise ValidationError(f"Row {index}: {exc}") from exc
            converted = {}
            for key, value in row.items():
                # Mitigate formula injection when CSVs are opened in spreadsheet apps.
                converted[key] = ("'" + value if isinstance(value, str) and
                                  value.lstrip().startswith(("=", "+", "-", "@")) and
                                  key not in INPUT_FIELDS else value)
            converted.update({k: "; ".join(v) if isinstance(v, list) else v
                              for k, v in result.items()})
            rows.append(converted)

    output_fields = fields + [k for k in OUTPUT_FIELDS if k not in fields]
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="UPCR / UACR ratio calculator (spot urine)")
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser("single", help="Calculate one spot urine result")
    for name in INPUT_FIELDS:
        single.add_argument("--" + name.replace("_", "-"), type=float)
    batch = commands.add_parser("batch", help="Convert named-column CSV data")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="results.csv")
    parsed = parser.parse_args(argv)
    try:
        if parsed.command == "single":
            result = calculate_metrics(**{k: getattr(parsed, k) for k in INPUT_FIELDS})
            print(json.dumps(result, indent=2, allow_nan=False))
        else:
            count = process_batch(parsed.input, parsed.output)
            print(f"Processed {count} records -> {parsed.output}")
    except (ValidationError, FileNotFoundError, PermissionError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
