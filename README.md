# UPCR / UACR Proteinuria Converter

Calculate urine protein-to-creatinine ratio (UPCR, also called PCR) and urine albumin-to-creatinine ratio (UACR, also called ACR) from spot urine measurements. Convert either measured ratio between **mg/g creatinine** and **mg/mmol creatinine**.

## Features

- Static, responsive browser calculator in `web/`; no backend or Python runtime is required.
- Single-case and batch CSV calculations in dependency-free Python.
- Optional estimated 24-hour albumin/protein excretion **only** when an independently determined creatinine excretion (g/day) is supplied.
- KDIGO albuminuria categories (A1, A2, A3) calculated from **UACR only**.
- CSV result export in browser and CLI; input validation and assay-discordance warnings.
- Optional FastAPI endpoint `POST /api/convert`.

**Important:** UPCR and UACR are different measurements. One cannot be calculated from the other without additional information (such as the urine albumin fraction). Neither spot ratio is a measured 24-hour urine collection. This calculator is for research, education, and supporting interpretation; it does not diagnose disease or prescribe treatment.

## Browser application

Open `web/index.html` in a modern browser, or run a local static server:

```bash
python -m http.server 8001 --directory web
```

Then open `http://localhost:8001`. Select **urine concentrations** (all mg/dL) or **measured ratios** (mg/g or mg/mmol). Enter only measurements you have. The results include both ratio units and, when relevant, albuminuria classification.

The GitHub Pages deployment workflow is in `.github/workflows/pages.yml`. A public Pages URL should be published only after the repository's GitHub Pages configuration and successful live deployment have been verified.

## Python CLI

Requires Python 3.10+; core ratio calculations have no third-party dependencies.

```bash
python upcr_uacr.py single --protein-mg-dl 20 --albumin-mg-dl 5 --creatinine-mg-dl 100
python upcr_uacr.py single --uacr-mg-g 30
python upcr_uacr.py batch -i sample.csv -o results.csv
```

In the first example, UPCR = 200 mg/g and UACR = 50 mg/g (KDIGO A2). The batch CSV headers are `protein_mg_dl`, `albumin_mg_dl`, `creatinine_mg_dl`, `upcr_mg_g`, `uacr_mg_g`, and optionally `creatinine_g_day`. At least one protein/albumin measurement or pre-calculated ratio is necessary. Other columns are retained in the output. Use measurements from the same specimen when calculating both ratios.

For the optional API:

```bash
python -m pip install -r requirements.txt
python cli.py serve --host 127.0.0.1 --port 8000
```

```bash
curl -X POST http://127.0.0.1:8000/api/convert \
  -H "Content-Type: application/json" \
  -d '{"albumin_mg_dl":5,"creatinine_mg_dl":100}'
```

The older `cli.py audit`, `cli.py chat`, agent and enrichment modules are retained for backward compatibility, but implement **demonstration-only thresholds and mocked responses**. They are not validated clinical decision support, clinical-grade de-identification, or a production security platform. Deploy the audit API only in a suitably restricted environment and configure `AUDIT_SECRET_KEY` for audit logging.

## Methods and clinical interpretation

For a matched urine specimen:

```text
ratio (mg/g creatinine) = analyte (mg/dL) / creatinine (mg/dL) × 1000
ratio (mg/mmol creatinine) = ratio (mg/g) × 0.11312
estimated analyte (mg/day) = ratio (mg/g) × supplied creatinine excretion (g/day)
```

Albuminuria (from UACR, mg/g):

| Category | UACR | Description |
| --- | --- | --- |
| A1 | <30 | Normal to mildly increased |
| A2 | 30 to <300 | Moderately increased |
| A3 | ≥300 | Severely increased |

Classification thresholds apply to UACR, **not** an arbitrary weighted score or UPCR. Clinical interpretation depends on persistence, eGFR, history, and biological and analytical variation.

References: [KDIGO CKD evaluation and management](https://kdigo.org/guidelines/ckd-evaluation-and-management/) and [NIDDK urine albumin assessment](https://www.niddk.nih.gov/health-information/professionals/clinical-tools-patient-management/kidney-disease/identify-manage-patients/evaluate-ckd/assess-urine-albumin).

## Privacy and security

The browser calculator uses local JavaScript and does not submit measurements to a server or store them in cookies or browser storage. CSV downloads are generated locally. Avoid entering identifying patient data. The optional Python backend and demonstration audit endpoints are separate services and may hold information in server process memory. No regular-expression filter guarantees comprehensive PHI detection or HIPAA compliance.

## Testing

```bash
python -m pip install -r requirements.txt
python -m pytest -q
node --test web/app.test.cjs
node --check web/app.js
```

GitHub Actions tests Python 3.10–3.12, browser calculations, and audit-chain tampering. Browser functionality needs no build step or Pyodide runtime.

## License

MIT — see [LICENSE](LICENSE).
