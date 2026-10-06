# SkillSetu AI

SkillSetu AI is a prototype platform for Recognition of Prior Learning (RPL). It helps a worker describe skills gained through work, organize evidence of those skills, and move an assessment through a human-led review process.

The application combines a multilingual worker experience with assessor tools, configurable trade packs, calibration views, and demo credential-verification integrations. It is designed for product demonstration and workflow testing—not as an accredited assessment or production certification service.

## What the application does

- **Worker journey:** enter a skills declaration, review suggested trade-pack matches, capture or describe evidence, follow assessment status, and view a skills-passport mock-up.
- **Trade-pack matching:** compare a declaration with the included trade packs and return ranked suggestions, matched and missing outcomes, and possible bridge training. The packs are sample application data, not official qualification standards.
- **Evidence and assessment:** record evidence and assessor scores against competency rubrics. Safety-critical failures can cap the suggested outcome, and assessors remain responsible for decisions.
- **Review workflow:** represent assessment states from registration and declaration through review, sign-off, credential issue, and appeal. The backend restricts state transitions.
- **Assessor and admin tools:** review and score assessments, inspect calibration summaries, and manage the demo trade-pack registry.
- **Access and offline demonstrations:** provide English, Hindi, Marathi, Tamil, and Bengali UI translations, accessibility and low-literacy controls, speech-browser API demonstrations, an installable PWA, and a Dexie-backed queue for evidence submissions.
- **Integration examples:** expose mock verification, revocation, CSV/PDF export, and external-push endpoints to demonstrate integration contracts.

AI-generated or heuristic output is advisory only. It does not make or issue a certification decision.

## Architecture

| Part | Technology | Location |
| --- | --- | --- |
| Web client | React, TypeScript, Vite, React Router | [`frontend/`](./frontend/) |
| Installable web app | Vite PWA plugin and service worker | [`frontend/vite.config.ts`](./frontend/vite.config.ts) |
| Offline action queue | Dexie / IndexedDB | [`frontend/src/App.tsx`](./frontend/src/App.tsx) |
| API | FastAPI, Pydantic, SQLAlchemy | [`backend/app/`](./backend/app/) |
| Local database | SQLite | Defaults to `./skillsetu.db` relative to the API process working directory |
| Sample data and reset helpers | Python | [`backend/app/seed_data.py`](./backend/app/seed_data.py), [`scripts/`](./scripts/) |
| Local container stack | Docker Compose | [`docker-compose.yml`](./docker-compose.yml) |

The API creates its database tables and adds missing demo users and candidates when it starts. SQLite files, generated signing keys, dependencies, and build output are local artifacts and are excluded from Git.

## Run locally

### Requirements

- Python 3.11
- Node.js 20 or later and npm
- Git

### 1. Start the backend

From the repository root, use PowerShell:

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt
Set-Location backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API and interactive OpenAPI documentation are available at:

- Health check: <http://localhost:8000/health>
- API docs: <http://localhost:8000/docs>

The first startup creates the local SQLite database and seeds demo accounts and candidate records.

### 2. Start the frontend

Open a second terminal at the repository root:

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Open <http://localhost:5173>. The development client calls the API at `http://localhost:8000`.

### Docker Compose

With Docker Desktop or another Docker Compose installation running:

```powershell
docker compose up --build
```

The Compose setup starts the API and Vite development server. Open <http://localhost:5173> for the app or <http://localhost:8000/docs> for the API. This setup is intended for development and demonstration, not production deployment.

## Demo accounts

The backend seeds these accounts on first startup:

| Role | Username | Password |
| --- | --- | --- |
| Administrator | `admin` | `admin123` |
| Assessor | `assessor1` | `assessor123` |
| Worker | `worker1` | `worker123` |

Additional seeded assessor and worker accounts are available as `assessor2` through `assessor8` and `worker2` through `worker60`; the seeded password for each group is the same as shown above. These credentials are public demo credentials and must never be used for real data or an internet-facing deployment.

## Main screens

| Screen | Route | Purpose |
| --- | --- | --- |
| Home | `/` | Entry point and role-based links |
| Sign in | `/login` | Authenticate a seeded demo user |
| Worker declaration | `/worker/declare` | Describe skills and see trade-pack suggestions |
| Demonstration and evidence | `/worker/demonstrate` | Capture or record evidence for an assessment |
| Skills passport | `/worker/passport` | View demo credential, QR, and recommendation content |
| Notifications | `/worker/notifications` | Preview mock worker notifications |
| Assessor scoring | `/assessor/score` | Review candidates and record competency scores |
| Trade-pack editor | `/admin/packs` | Validate and save the demo trade-pack registry |
| Calibration | `/calibration` | View demo assessor-calibration and explainability data |
| Certificate | `/certificate` | View the certificate demonstration |
| Credential verification | `/verify/:id` | Open the public verification view for an assessment |

## Assessment lifecycle

The backend models the following states:

```text
Registered → Declared → Evidence captured → Under review
           → Second review / Moderation (when applicable)
           → Signed off → Credential issued → Appeal (if needed)
```

Not every assessment follows every branch. Valid transitions are checked by the API; the worker-facing status tracker displays the lifecycle.

## API overview

FastAPI provides the full request and response schemas in `/docs`. The main endpoint groups include:

| Area | Example endpoints |
| --- | --- |
| Health and authentication | `GET /health`, `POST /api/auth/login`, `GET /api/me` |
| Competencies and trade packs | `GET /api/competencies`, `GET /api/trade-packs`, `POST /api/trade-packs/validate` |
| Worker declaration and evidence | `POST /api/declare`, `POST /api/assessments`, `POST /api/evidence` |
| Assessor workflow | `GET /api/candidates`, `GET /api/assessments`, `POST /api/score`, `PATCH /api/assessments/{id}/status` |
| Calibration | `GET /api/calibration` and related `/api/calibration/*` routes |
| Credentials | `GET /api/certificate/{id}`, `GET /api/public/verify/{id}` |
| Demo integrations | `/api/integrations/*`, `/api/public/vc/verify/{credential_id}` |
| Audit | `GET /api/audit` |

Most assessment and integration operations require a bearer token or the configured demo API key. Consult `/docs` for the endpoint-specific authorization requirements.

## Development and tests

### Backend tests

From the repository root with the backend virtual environment activated:

```powershell
Set-Location backend
python -m pytest -q --ignore=tests/test_e2e_flow.py
```

The excluded `test_e2e_flow.py` test is an HTTP integration test against a running API. Start the backend in one terminal, then run that test from a second terminal:

```powershell
Set-Location backend
python -m pytest -q tests/test_e2e_flow.py
```

The API seeds the demo users used by the flow test when it starts.

### Frontend build and lint

From the repository root:

```powershell
Set-Location frontend
npm ci
npm run build
npm run lint
```

The build runs the TypeScript project checks before creating the Vite production bundle.

## Included trade packs

The registry currently includes sample packs for:

- Domestic Electrician
- Plumber (General)
- Mason
- Tailor / Sewing Machine Operator
- Domestic Data Entry Operator

The pack data includes qualification references, outcome descriptions, rubrics, checklists, safety-critical steps, and version information. Treat all included pack content as demonstration material until validated by the relevant awarding and regulatory bodies.

## Prototype boundaries

- **Not an official certification system:** qualification references, trade packs, assessment data, and generated credentials are illustrative. The app is not connected to Skill India Digital, DigiLocker, NCVET, an SSC, or another government service.
- **Human sign-off is required:** matching, scoring drafts, calibration summaries, and recommendations are advisory. A human assessor is responsible for assessment outcomes and credential sign-off.
- **Synthetic metrics:** seeded candidates, assessor calibration values, A/B summaries, and recommendations are mock or pilot-style data, not measured field results.
- **Heuristic matching and evidence checks:** lexical matching and optional sentence embeddings are not a certified occupational benchmark. Video checks are demo heuristics, not production liveness or biometric validation.
- **Mock integrations:** credential signatures, public verification, revocations, exports, notifications, and external delivery behavior demonstrate interfaces only. Local signing keys are generated for the demo and are not a managed production trust infrastructure.
- **Limited offline behavior:** the app shell can be installed and selected worker actions can be queued locally. API-dependent workflows still need a reachable backend; queue behavior is not a guarantee of complete offline operation or conflict-free synchronization.
- **Development security defaults:** the backend uses demo secrets and permissive local CORS configuration. Authentication, key management, authorization, privacy, retention, transport security, and deployment configuration need a production security review before any real-user use.

Do not submit real personal, assessment, credential, or other sensitive data to this prototype.

## Repository layout

```text
.
├── backend/
│   ├── app/                 # API, models, workflow, matching, integrations
│   ├── tests/               # Backend unit and integration tests
│   ├── requirements.txt     # Backend runtime dependencies
│   └── requirements-dev.txt # Runtime plus test/development dependencies
├── frontend/
│   ├── public/              # PWA assets
│   ├── src/                 # React application
│   ├── package.json
│   └── package-lock.json
├── scripts/                 # Demo seed and reset helpers
├── docker-compose.yml
└── README.md
```
