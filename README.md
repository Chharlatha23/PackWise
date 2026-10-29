# PackWise — Evidence-Driven Inverse-Design Food Packaging Recommendation System

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
- **Stack:** Vite, React 19, TypeScript, Vanilla CSS design system with Lucide icons.
- **Persistent Collapsible Navigation:** Clean, modern sidebar (collapses to icons on desktop, slides out as drawer on mobile) organizing features into three logical tiers:
  - **WORKSPACE:**
    - **Overview:** System topology status, database counts (commodities, films, barrier observations, traceable records), active solver tier status, and quick workflow launch cards.
    - **Recommendation Engine:** 4-step guided inverse-design wizard (*Commodity Profile* ➔ *Storage & Logistics* ➔ *Scientific Properties* ➔ *Package Geometry & Solver Tier*) with quick commodity presets (Strawberry, Apple, Salmon) and clear epistemic uncertainty indicators.
    - **Package Comparison:** Dedicated side-by-side material property comparison matrix evaluating thickness, $OTR$, $CO_2TR$, and $WVTR$ across canonical films.
    - **What-If Analysis:** Parameter stress-testing suite evaluating temperature abuse, relative humidity shifts, and logistics transit duration against the live backend scientific engine.
  - **VALIDATION & EVIDENCE:**
    - **Evidence Library:** Searchable scientific catalog of canonical records, data sources (USDA, UC Davis, CIRAD/WUR), and experimental barrier measurements.
    - **Trial Feedback & Audit:** Empirical trial observation ledger with predicted vs. observed residual tracking and structured model update candidate submission for human review (strict M12 feedback-loop governance with no automated retraining).
    - **Model Performance:** Detailed architectural audit page clarifying M9 (Deterministic Baseline), M10 (Adaptive Heuristic), and M11 (Surrogate-Assisted Search) with the mandatory exact-physics validation gateway.
  - **SYSTEM:**
    - **Settings:** Environment configuration, database topology details (MySQL user accounts + SQLite scientific knowledge base), and OAuth security auditing.
- **Top Header Bar:** Subtle backend API status indicator (`API Connected` / `Disconnected`), user profile avatar, authenticated email badge, and secure sign-out.
- **Recommendation Results View:** FEASIBLE / INFEASIBLE / UNKNOWN status badges, candidate packaging materials, interval-preserving objective ranges, barrier properties, explainability counterfactuals, and non-dominated Pareto front candidates verified exclusively through exact physics.

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
| **Testing** | pytest (503 passed in backend/tests/; 0 failures, 70 warnings), httpx |
| **Frontend UI** | Vite, React 19, TypeScript, Tailwind CSS |
| **Authentication** | Google OAuth 2.0 (Authorization Code + PKCE/CSRF state), Authlib, python-jose (JWT) |

---

## Web Application Routes & Authentication

### 1. Route Structure
- **`/` (Landing Page):** Minimal, high-aesthetic presentation of PackWise adhering to warm brown (`#4A3B32`) and cream (`#FDFBF7`) palette. Features hero copy (*"Plan better food packaging with AI"*), responsive two-column layout, and photograph of eco-friendly kraft paper packaging.
- **`/login` (Login Page):** Dedicated sign-in portal with PackWise branding, "Continue with Google" OAuth initiation, error alert handling, and return navigation.
- **`/dashboard` (Protected Dashboard):** Unauthenticated users attempting to access the dashboard or inverse-design recommendation engine are automatically redirected to `/login`. Authenticated users display profile avatar, email, and one-click Sign Out.

### 2. Google OAuth 2.0 Setup

PackWise uses an Authorization Code Flow with backend CSRF `state` validation and signed JWT access tokens.

#### Environment Variables (`.env`)
Configure the following in the repository root `.env` (refer to `.env.example`):
```env
# Frontend & Origins
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000

# Google OAuth 2.0 Credentials (Backend Only — Never expose to frontend or git)
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# JWT Token Secret
AUTH_SECRET_KEY=generate_a_secure_random_secret_key_here
```

#### Google Cloud Console Configuration
1. Go to **Google Cloud Console** > **APIs & Services** > **Credentials**.
2. Create an **OAuth 2.0 Client ID** (Application type: *Web application*).
3. Under **Authorized JavaScript origins**, add:
   - `http://localhost:5173`
   - `http://127.0.0.1:5173`
   - `http://localhost:8000`
4. Under **Authorized redirect URIs**, add:
   - `http://localhost:8000/api/v1/auth/google/callback`
5. Copy the generated **Client ID** and **Client Secret** into your `.env` file.

> **Note on Testing:** The automated backend test suite validates OAuth initiation, state generation/verification, mock token exchange, user creation, session expiration, and route protection (7 dedicated tests in `backend/tests/test_auth.py`). Live Google authentication requires valid Google Cloud credentials in your local `.env`.

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
python -c "from app.core.database import engine, Base, SessionLocal; from app.ingestion.pipeline import DataIngestionPipeline; from app.models.feedback import PackagingFeedbackRecord, ModelUpdateCandidate; from app.models.user import User; Base.metadata.create_all(bind=engine); db = SessionLocal(); pipeline = DataIngestionPipeline(db); pipeline.run(); print('DB Ready!')"
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
# Output: 503 passed, 70 warnings in ~36.05s
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

