# 🌾 Zamin X — Land Litigation Intelligence Platform

> **"Know your land. Know its truth."**
>
> An AI-powered platform that lets any rural Indian verify if land has active
> court cases — in seconds, in Tamil, on a ₹1,500 phone.

---

[![Tests](https://img.shields.io/badge/tests-39%20passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-orange)](https://xgboost.readthedocs.io)
[![License](https://img.shields.io/badge/license-Proprietary-red)](LICENSE)

**Team**: Project Minds Guilders — JKKM College of Technology, Erode  
**Event**: NEN Ignite Bootcamp (Niral Thiruvizha 3.0) — Wadhwani Foundation  
**Team Lead**: Praveen Raja P | Members: Akhil Dev P, Hasarudeen, Gowri R

---

## 📋 Table of Contents

1. [The Problem](#the-problem)
2. [The Solution](#the-solution)
3. [Architecture](#architecture)
4. [Project Structure](#project-structure)
5. [Quick Start](#quick-start)
6. [API Reference](#api-reference)
7. [AI Models](#ai-models)
8. [Training the Model](#training-the-model)
9. [Deployment](#deployment)
10. [Roadmap](#roadmap)

---

## 🚨 The Problem

**66% of Indian civil cases are land disputes. 40 million+ cases pending in courts.**

Rural Indians have no simple, affordable way to check if land carries active court
cases before buying or selling. Court records exist — but they're buried in complex
legal databases. Hiring a lawyer costs more than most rural families earn in a month.

**A single disputed land transaction can wipe out a family's lifetime savings.**

---

## ✅ The Solution

Zamin X (also called **NiralCheck**) is an AI-powered mobile-first web app that:

| Feature | Description |
|---------|-------------|
| 🔍 **Instant Search** | Enter village name + survey number → get results in < 3 seconds |
| ⚖️ **Live Court Data** | Scraped from eCourts India and NJDG (updated every 6 hours) |
| 🤖 **AI Summaries** | MuRIL NLP converts dense legal text into plain Tamil / Hindi |
| 📊 **Risk Score** | XGBoost fraud risk score (0–100) with explainable risk factors |
| 🔗 **Blockchain Badge** | Polygon + Hyperledger Fabric tamper-proof audit trail (Phase 3) |
| 📲 **SMS / WhatsApp Alerts** | Notify subscribers when case status changes |
| 📷 **OCR Scan** | Photo your patta/chitta document → auto-extract survey number |
| 🏢 **B2B Bulk API** | Process 100 parcels in one API call for real estate firms |

**Built for ₹1,500 phones on 2G networks — because real inclusion means reaching the last mile.**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ZAMIN X ARCHITECTURE                  │
├─────────────────┬───────────────┬───────────────────────┤
│   Mobile App    │  Web Browser  │    B2B API Client     │
│  (React Native) │  (React PWA)  │   (Python/REST)       │
└────────┬────────┴───────┬───────┴───────────┬───────────┘
         │                │                   │
         └────────────────▼───────────────────┘
                    ┌─────────────┐
                    │  FastAPI    │  ← JWT Auth, Rate Limiting
                    │  Backend   │    Prometheus Metrics
                    └──────┬──────┘
              ┌────────────┼────────────────┐
              ▼            ▼                ▼
        ┌──────────┐ ┌──────────┐  ┌──────────────┐
        │PostgreSQL│ │  Redis   │  │Celery Workers│
        │(Primary) │ │(Cache+  │  │- eCourts     │
        │          │ │ Queue)  │  │  Scraper     │
        └──────────┘ └──────────┘  │- Alert Sender│
                                   │- Risk Scorer │
              ┌────────────────────└──────────────┘
              ▼
        ┌─────────────────────────────────────┐
        │         AI / NLP ENGINE             │
        │  MuRIL (Legal NLP Summarizer)       │
        │  XGBoost (Fraud Risk Scorer)        │
        │  Tesseract 5 (OCR for patta docs)   │
        │  FAISS (Semantic case search)       │
        └─────────────────────────────────────┘
              ▼
        ┌─────────────────────────────────────┐
        │      BLOCKCHAIN LAYER (Phase 3)     │
        │  Hyperledger Fabric (private chain) │
        │  Polygon Mumbai (public anchor)     │
        └─────────────────────────────────────┘
```

---

## 📁 Project Structure

```
zamin_x/
├── api/                        # FastAPI application layer
│   ├── app.py                  # Main FastAPI app, lifespan, middleware
│   ├── auth.py                 # JWT authentication, Firebase OTP
│   ├── schemas.py              # Pydantic request/response models
│   └── routers/
│       ├── search.py           # POST /api/search  ← CORE ENDPOINT
│       ├── auth.py             # POST /api/auth/register, /login
│       ├── ocr.py              # POST /api/ocr/extract
│       ├── risk.py             # GET  /api/risk-score/:survey_id
│       ├── alerts.py           # POST /api/alerts/subscribe
│       ├── bulk.py             # POST /api/bulk/cases (B2B)
│       └── verify.py           # POST /api/verify (blockchain)
│
├── src/                        # Core business logic
│   ├── config.py               # Settings (Pydantic + env vars)
│   ├── database.py             # Async SQLAlchemy engine + session
│   ├── models.py               # ORM models (9 tables)
│   ├── data_loader.py          # eCourts scraper + mock data generator
│   ├── preprocessing.py        # Legal text cleaning + OCR image prep
│   ├── feature_engineering.py  # 22-feature vector for XGBoost
│   ├── model.py                # NLP summarizer, Risk scorer, OCR, FAISS
│   ├── predict.py              # Search pipeline orchestrator
│   ├── train.py                # XGBoost training + Optuna HPO
│   ├── evaluate.py             # Evaluation plots + metrics
│   ├── celery_tasks.py         # Background jobs (scraping, alerts)
│   └── notifications.py        # SMS/WhatsApp/Push via Twilio + FCM
│
├── config/
│   └── config.yaml             # Central configuration file
│
├── data/
│   ├── raw/                    # Raw scraped court data
│   └── processed/              # Cleaned, feature-engineered data
│
├── models/                     # Trained model files
│   ├── xgboost_risk_scorer.pkl # Trained XGBoost model
│   ├── muril_finetuned/        # Fine-tuned MuRIL model (Phase 2)
│   └── faiss_index.bin         # Semantic search index
│
├── tests/
│   └── test_model.py           # 39-test suite (100% pass rate ✅)
│
├── reports/                    # Evaluation plots (auto-generated)
│
├── main.py                     # CLI entry point (server/train/demo/seed)
├── docker-compose.yml          # Full stack: API + PostgreSQL + Redis + Celery
├── Dockerfile                  # Multi-stage production Docker build
├── requirements.txt            # Python dependencies
└── .env.example                # Environment variable template
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (recommended)
- Tesseract OCR (`apt install tesseract-ocr tesseract-ocr-tam`)

### Option A — Docker (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/pmg/zaminx.git
cd zaminx

# 2. Configure environment
cp .env.example .env
# Edit .env with your secrets

# 3. Start all services
docker-compose up -d

# 4. API is live at http://localhost:8000
# 5. Swagger UI at http://localhost:8000/docs
```

### Option B — Local Development

```bash
# 1. Install Python deps
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
export DB_HOST=localhost DB_PASSWORD=your_pw ...

# 3. Initialize database
python main.py migrate

# 4. Seed sample Tamil Nadu court data
python main.py seed

# 5. Train the risk scorer
python main.py train

# 6. Start API server (auto-reload)
python main.py server --reload

# 7. API at http://localhost:8000/docs
```

### Quick Demo (No Server Needed)

```bash
# Search for court cases on a specific land parcel
python main.py demo --village Gobichettipalayam --survey 123/4 --language ta
```

Expected output:
```
============================================================
  ZAMIN X — Land Litigation Report
============================================================
  Village     : Gobichettipalayam
  Survey No.  : 123/4
  District    : Erode
  Area        : 3.14 acres
------------------------------------------------------------
  Total Cases : 2
  Active      : 2
  Disposed    : 0
------------------------------------------------------------
  Risk Score  : 45.0/100
  Risk Level  : MEDIUM
  Risk Factors:
    • 2 active court case(s) found
    • Boundary dispute detected — high complexity
------------------------------------------------------------
  Blockchain  : ⏳ not_anchored
============================================================
```

---

## 📡 API Reference

### Core Endpoints

#### `POST /api/search` — Land Litigation Search

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "village_name": "Gobichettipalayam",
    "survey_number": "123/4",
    "state": "TN",
    "language": "ta"
  }'
```

**Response:**
```json
{
  "land_record": {
    "survey_id": "uuid-here",
    "village_name": "Gobichettipalayam",
    "survey_number": "123/4",
    "district": "Erode",
    "area_acres": 3.14,
    "patta_number": "P4521"
  },
  "cases": [
    {
      "case_number": "OS/234/2022",
      "court_name": "District Court, Erode",
      "case_type": "Boundary Dispute",
      "status": "active",
      "next_hearing": "2026-06-15T00:00:00",
      "orders": [
        {
          "order_date": "2026-03-10T00:00:00",
          "summary_tamil": "[AI-generated Tamil summary]",
          "key_issue": "Boundary demarcation dispute",
          "urgency_level": "medium"
        }
      ]
    }
  ],
  "risk_assessment": {
    "risk_score": 45.0,
    "risk_level": "medium",
    "risk_factors": [
      "2 active court case(s) found",
      "Boundary dispute detected — high complexity"
    ]
  },
  "blockchain_badge": {
    "verified": false,
    "status": "not_anchored",
    "message": "Blockchain verification coming in Phase 3"
  },
  "search_metadata": {
    "total_cases": 2,
    "active_cases": 2,
    "response_time_ms": 312,
    "cache_hit": false
  }
}
```

#### `POST /api/ocr/extract` — Scan Patta Document

```bash
curl -X POST http://localhost:8000/api/ocr/extract \
  -H "Authorization: Bearer <token>" \
  -F "file=@patta_document.jpg"
```

#### `POST /api/bulk/cases` — B2B Bulk Lookup (100 parcels)

```bash
curl -X POST http://localhost:8000/api/bulk/cases \
  -H "Authorization: Bearer <b2b-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"village_name": "Erode", "survey_number": "456/2"},
      {"village_name": "Bhavani", "survey_number": "789/1"}
    ],
    "language": "en"
  }'
```

#### `GET /api/health` — System Health Check

```bash
curl http://localhost:8000/api/health
```

Full Swagger UI available at: **http://localhost:8000/docs**

---

## 🤖 AI Models

### 1. Legal NLP Summarizer (MuRIL)

| Property | Value |
|----------|-------|
| Base Model | `google/muril-base-cased` (236M params) |
| Fine-tuning Data | ILDC dataset (IIT Bombay) + eCourts public orders |
| Output | 2-sentence Tamil / Hindi summary |
| Inference Time | < 2 seconds (CPU) |
| Fallback | Extractive summarization (TF-IDF) |

### 2. Fraud Risk Scorer (XGBoost)

| Property | Value |
|----------|-------|
| Algorithm | XGBoost Classifier |
| Features | 22 features (case count, types, ownership, court level) |
| Training Data | 5,000 synthetic samples (Phase 1) → real eCourts data (Phase 2) |
| Output | Risk score 0–100 + risk level (low/medium/high/critical) |
| CV AUC | ~0.89 on synthetic data |

**Top Features by Importance:**
1. `active_case_count` — Number of active cases
2. `has_boundary_dispute` — Boundary dispute flag
3. `rapid_transfer_flag` — 2+ transfers within 12 months
4. `has_high_court_case` — Case elevated to High Court
5. `active_case_ratio` — Active / Total cases ratio

### 3. OCR Extractor (Tesseract 5)

| Property | Value |
|----------|-------|
| Engine | Tesseract 5 (LSTM) |
| Languages | Tamil (`tam`) + Hindi (`hin`) + English (`eng`) |
| Preprocessing | OpenCV: resize, denoise, adaptive threshold, deskew |
| Extracts | Survey number, village name, patta number |

---

## 🏋️ Training the Model

```bash
# Train with default hyperparameters
python main.py train

# Train with Optuna hyperparameter tuning (50 trials)
python main.py train --tune

# Train on your own labeled CSV
python main.py train --data data/processed/training_data.csv

# Evaluate saved model + generate all plots
python main.py evaluate
```

Training CSV format:
```
total_case_count,active_case_count,...,rapid_transfer_flag,risk_label
3,2,...,0,1
0,0,...,0,0
```

Evaluation outputs saved to `reports/`:
- `confusion_matrix.png`
- `roc_curve.png`
- `precision_recall.png`
- `feature_importance.png`
- `risk_distribution.png`
- `calibration.png`

---

## 🐳 Deployment

### Docker Production

```bash
# Build production image
docker build -t zaminx:latest .

# Run with production env
docker-compose -f docker-compose.yml up -d

# Scale API workers
docker-compose up --scale api=3 -d
```

### AWS Deployment

```bash
# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
docker tag zaminx:latest $ECR_URI/zaminx:latest
docker push $ECR_URI/zaminx:latest

# Deploy to ECS Fargate (see infrastructure/ecs-task.json)
aws ecs update-service --cluster zaminx-prod --service api --force-new-deployment
```

### Environment Variables (Production)

```bash
# Required
SECRET_KEY=<64-char-random-string>
DB_HOST=your-rds-endpoint.ap-south-1.rds.amazonaws.com
DB_PASSWORD=<strong-password>
REDIS_HOST=your-elasticache-endpoint
ENVIRONMENT=production

# For SMS alerts
TWILIO_ACCOUNT_SID=ACxx...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE=+1234567890

# For blockchain (Phase 3)
POLYGON_RPC_URL=https://polygon-rpc.com
POLYGON_PRIVATE_KEY=...
```

### CI/CD (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=src --cov-report=xml

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
      - run: docker build -t zaminx . && docker push $ECR_URI/zaminx:latest
      - run: aws ecs update-service --force-new-deployment ...
```

---

## 🗺️ Roadmap

| Phase | Timeline | Milestone |
|-------|----------|-----------|
| **Phase 1** ✅ | Month 1-3 | MVP: Search + Mock eCourts + Risk Score + Tamil NLP |
| **Phase 2** 🚧 | Month 4-6 | Live eCourts API + Fine-tuned MuRIL + SMS Alerts |
| **Phase 3** 📅 | Month 7-10 | Blockchain (Polygon + HLFabric) + Map visualization |
| **Phase 4** 📅 | Month 11-14 | Voice input (Whisper) + Offline mode + Karnataka expansion |
| **Phase 5** 📅 | Month 15-18 | National rollout + Government API MoU |

---

## 🧪 Running Tests

```bash
# Run all 39 tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov=api --cov-report=term-missing

# Run specific test class
pytest tests/test_model.py::TestFraudRiskScorer -v
```

**Test Coverage:**
- Feature engineering: 7 tests
- Risk scorer: 6 tests
- NLP summarizer: 5 tests
- Text preprocessor: 5 tests
- Training pipeline: 3 tests
- API schemas: 5 tests
- Mock data generator: 7 tests
- Search pipeline integration: 1 test

---

## 📊 Year 1 Financial Projections

| Metric | Value |
|--------|-------|
| Projected Revenue | ₹12 Lakhs |
| Projected Profit | ₹5.5 Lakhs |
| Profit Margin | 46% |
| Business Model | Subscription (Free/Basic ₹99/Premium ₹299/B2B ₹999) |

---

## 🛡️ Ethical Commitments

- **No raw Aadhaar storage** — only SHA-256 hashes
- **DPDP Act 2023 compliant** — data minimization, consent-first
- **No lawyer replacement** — tool for awareness, not legal advice
- **Open to audit** — all blockchain anchors are publicly verifiable
- **Affordable** — Free tier for rural citizens; paid tiers for businesses

---

## 📞 Contact

**Praveen Raja P** (Project Leader)  
JKKM College of Technology, Erode, Tamil Nadu  
📧 contact@zaminx.in  

**Team**: Akhil Dev P | Hasarudeen | Gowri R

---

*Built with ❤️ for rural India. Zamin X — because every family deserves to know the truth about their land.*
