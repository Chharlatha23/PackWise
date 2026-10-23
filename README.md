# PackWise — AI Food Packaging Optimizer

An **evidence-driven inverse-design decision-support system** for food packaging material recommendation based on physics-informed kinetics, multi-objective optimization, and traceable scientific evidence.

> **PROJECT STATUS:** Stages M1–M12 verified. Full scientific pipeline implemented across backend, scientific engine, database models, and interactive React frontend.

---

## Architecture & System Workflow

The system operates strictly according to the frozen scientific hierarchy:

```
[ Packaging Request ]
         │
         ▼
[ Evidence Retrieval & Ingestion ] ────► Canonical Database (PostgreSQL / SQLite)
         │
         ▼
[ Property Inference Engine ] ─────────► Multi-tier resolution with epistemic uncertainty (Levels A/B/D)
         │
         ▼
[ Packaging Requirement Engine ] ──────► Respiration kinetics, EMAP gas exchange (O2/CO2), WVTR permeation
         │
         ▼
[ Hard-Constraint Evaluator ] ─────────► Feasibility classification: FEASIBLE, INFEASIBLE, UNKNOWN
         │
         ▼
[ Inverse-Design Search Engine ]
   ├── M9:  Deterministic Baseline (Exhaustive lattice enumeration)
   ├── M10: Adaptive Heuristic Search (Deterministic candidate prioritization; no learned ML)
   └── M11: Surrogate-Assisted Search (Surrogate ranking with OOD checks; exact-physics verification required)
         │
         ▼
[ Exact-Physics Verification ] ────────► Authoritative gateway: only verified candidates enter Pareto front
         │
         ▼
[ Non-Dominated Pareto Front ] ────────► 4-objective evaluation (Thickness, Moisture, Gas, Shelf-Life Margin)
         │
         ▼
[ Explainability & Counterfactuals ] ──► Constraint audit, critical flip thresholds, literature citations
         │
         ▼
[ Empirical Feedback & Audit Ledger ] ──► Real-world observation logging, residual tracking, human review flag
```

---

## Implemented Capabilities

### 1. Backend Core & Scientific Engine
- **Input Validation:** Strict structural validation via Pydantic schemas (`PackagingRequest`).
- **Evidence Modeling & Database:** Relational schema supporting sources, evidence records, and observations across `food_observation`, `respiration_observation`, and `material_barrier_observation`.
- **Property Inference (`PropertyInferenceEngine`):** Hierarchical resolution of commodity transpiration, respiration, and composition with uncertainty tracking. Missing properties remain strictly `UNKNOWN`.
- **Requirements Calculation (`PackagingRequirementEngine`):** Closed-form kinetics for Michaelis-Menten respiration, package gas permeation, and steady-state moisture balance.
- **Feasibility Evaluation (`HardConstraintEvaluator`):** Evaluates candidates against barrier and shelf-life constraints without zero-coercion or midpoint collapsing.
- **Search Tiers:**
  - **M9 (Deterministic Baseline):** Exhaustive evaluation across material lattice candidates.
  - **M10 (Adaptive Heuristic):** Heuristic prioritization for candidate search (purely heuristic; no learned ML).
  - **M11 (Surrogate-Assisted):** Machine-learning surrogates guide search ordering; **exact-physics evaluation remains authoritative** and all Pareto candidates must pass exact physics.
- **Pareto Optimization:** Non-dominated sorting across four physical objectives (`f_thickness`, `f_moisture_margin`, `f_gas_alignment`, `f_shelf_life_margin`).
- **Explainability & Counterfactuals (`ExplainabilityEngine`):** Candidate feasibility rationales and critical threshold shift calculations (`BECOMES_INFEASIBLE_IF`, `BECOMES_FEASIBLE_IF`).
- **Empirical Feedback (`FeedbackService` & `FeedbackEngine`):** Ingestion of observed trial measurements (`POST /api/v1/feedback`), predicted vs. observed residual comparisons, and structured `model_update_candidate` creation. **Zero automatic retraining occurs**, preserving scientific reproducibility.

### 2. Frontend User Interface
- **Stack:** Vite, React, TypeScript, Tailwind CSS.
- **Request Form:** Interactive form with commodity presets (Strawberry, Apple, Salmon) and search tier selection (M9, M10, M11).
- **Recommendation Dashboard:** Displays inferred food properties with epistemic status, calculated scientific requirements, KPI summaries, and active solver metadata.
- **Pareto Candidate Cards:** Shows interval-preserving objective ranges, evaluation profiles, and trade-off summaries.
- **Constraint Audit Modal:** Explains feasibility states, constraint thresholds, counterfactual boundaries, and literature citations.
- **Empirical Feedback Modal:** Ingests observed trial measurements and displays immediate comparison residuals and containment statuses.
- **Trial & Model Audit Ledger:** Dashboard tab for reviewing recorded empirical trials and discrepancies flagged for expert review.

---

## Core Scientific Principles

- **Rules First, Physics First, AI Only Where Verified:** Exact-physics evaluation is always authoritative. Surrogates only assist candidate shortlisting.
- **Strict Unknown Handling:** Missing evidence remains `UNKNOWN` with `None` values. The system never fabricates or hallucinates unverified numbers.
- **Interval Preservation:** Physical intervals `[min, max]` are preserved throughout all objective and counterfactual computations without collapsing to scalar midpoints.
- **Frozen Models & Human Governance:** Feedback records and discrepancies are logged as review candidates. Automated online retraining is explicitly prohibited.

---

## Current Limitations

- **No Live Model Retraining:** The system logs model update candidates for offline human expert review; it does not perform automated online parameter recalibration.
- **No Non-Physical Economic Scoring:** Scalar ranking, arbitrary cost proxies, and composite "best material" scores are excluded to maintain scientific objectivity.
- **Physical Validation Scope:** While tested against canonical published datasets (USDA, UC Davis, CIRAD/WUR, PolyID, ComBase), physical packaging trials were not conducted as part of this software repository.

---

## Technology Stack

| Component | Stack |
|-----------|-------|
| **Backend Core** | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 |
| **Scientific & ML Libraries** | NumPy, SciPy, scikit-learn |
| **Database** | PostgreSQL (schema & migrations) / SQLite (local fallback) |
| **Testing** | pytest (492 passing unit and integration tests), httpx |
| **Frontend UI** | Vite, React 19, TypeScript, Tailwind CSS |

---

## Setup & Running

### 1. Backend Setup

```bash
# Create and activate virtual environment
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install "psycopg[binary]"
```

Initialize local database:
```bash
python -c "from app.core.database import engine, Base, SessionLocal; from app.ingestion.pipeline import DataIngestionPipeline; from app.models.feedback import PackagingFeedbackRecord, ModelUpdateCandidate; Base.metadata.create_all(bind=engine); db = SessionLocal(); pipeline = DataIngestionPipeline(db); pipeline.run(); print('DB Ready!')"
```

Run FastAPI server:
```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Root: `http://127.0.0.1:8000/`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

Run full test suite:
```bash
pytest backend/tests/ -v
```

### 2. Frontend Setup

```bash
cd frontend
npm install
```

Run Vite development server:
```bash
npm run dev -- --host 127.0.0.1 --port 5173
```
- Web Application: `http://127.0.0.1:5173/`

Build for production:
```bash
npm run build
```

---

## Data Collection & Reference Sources

Evidence datasets are cataloged in `data/` and `docs/`:
- **USDA FoodData Central:** Proximate composition baseline.
- **USDA Handbook 66 & UC Davis Produce Facts:** Postharvest respiration rates and gas tolerances.
- **ComBase:** Microbial proliferation kinetics.
- **CIRAD/WUR & Manufacturer TDS:** Packaging film barrier properties ($OTR$, $CO_2TR$, $WVTR$).
