# UPCR UACR Proteinuria Converter

> **Domain:** Computational Biology & Clinical Chemistry
> **Standards:** CLSI, IUPAC

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)

---

## What It Does

Urine Protein-to-Creatinine (UPCR) & UACR Converter converts spot urine protein/albumin and creatinine ratios to estimated 24-hour excretion rates. Provides clinical classification and recommendations based on calculated scores.

- Single case evaluation via CLI
- Batch CSV processing
- FastAPI REST API server
- HMAC-SHA256 tamper-evident audit trail
- Zero-PHI outbound guard

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/upcr-uacr-proteinuria-converter.git
cd upcr-uacr-proteinuria-converter

# Install dependencies
pip install -r requirements.txt

# Set up environment configuration
cp .env.example .env
# Edit .env and set a secure AUDIT_SECRET_KEY
```

---

## Usage

### Single Case Evaluation
```bash
python upcr_uacr.py single --v1 14.5 --v2 4.2 --v3 1.8
```

### Batch CSV Processing
```bash
python upcr_uacr.py batch -i sample.csv -o results.csv
```

### Enterprise CLI (with audit trail)
```bash
# Set audit key first
export AUDIT_SECRET_KEY="your-secure-key-here"

# Run audit
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch processing
python cli.py batch -i sample.csv -o results.csv

# Verify audit trail
python cli.py verify-audit
```

### REST API Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

API Endpoints:
- `GET /health` - Health check
- `GET /metrics` - System metrics
- `POST /api/audit` - Submit task for evaluation
- `POST /api/chat` - Query supervisory chat
- `GET /api/audit/logs` - View audit trail

---

## Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `v1` | Primary measurement (urine protein) | Optional (default: 10.0) |
| `v2` | Secondary measurement (creatinine) | Optional (default: 5.0) |
| `v3` | Tertiary measurement (albumin) | Optional (default: 2.0) |

---

## Classification Tiers

| Score Range | Classification | Recommendation |
|:------------|:---------------|:---------------|
| < 10.0 | Low / Standard | Standard monitoring |
| 10.0 - 24.9 | Moderate / Intermediate | Close observation |
| >= 25.0 | High / Severe | Urgent clinical intervention |

---

## Security

- **Zero-PHI Outbound Guard:** AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers
- **HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation
- **Input Validation:** All numeric inputs validated for type, finiteness, and non-negativity
- **Secure Defaults:** No hardcoded secrets; AUDIT_SECRET_KEY must be configured via environment

---

## Testing

```bash
# Run all tests
pytest -v

# Run specific test files
pytest test_upcr_uacr.py -v
pytest tests/ -v
```

---

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run manually
docker build -t upcr-uacr-proteinuria-converter .
docker run -p 8000:8000 --env-file .env upcr-uacr-proteinuria-converter
```

---

## Project Structure

```
upcr-uacr-proteinuria-converter/
├── upcr_uacr.py          # Core conversion algorithm & CLI
├── cli.py                # Enterprise CLI with audit trail
├── enrichment.py         # Enrichment feature engines
├── simulator.py          # High-throughput simulation
├── agents/               # Enterprise agent framework
│   ├── base.py           # Security, PHI guard, audit trail
│   ├── models.py         # Pydantic data models
│   ├── supervisor.py     # Multi-agent orchestrator
│   ├── workers.py        # Specialized evaluation workers
│   ├── api.py            # FastAPI REST endpoints
│   └── ...
├── tests/                # Test suite
├── web/                  # Web dashboard
├── requirements.txt      # Python dependencies
├── Dockerfile            # Container build
└── docker-compose.yml    # Container orchestration
```
