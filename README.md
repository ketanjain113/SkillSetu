# SkillSetu AI

SkillSetu AI is a prototype platform for Recognition of Prior Learning (RPL). It helps a worker describe skills gained through work, organize evidence of those skills, and move an assessment through a human-led review process.

The application combines a multilingual worker experience with assessor tools, configurable trade packs, calibration views, and demo credential-verification integrations. It is designed for product demonstration and workflow testing—not as an accredited assessment or production certification service.

## What the application does

- **Worker journey:** enter a skills declaration, review suggested trade-pack matches, capture or describe evidence, follow assessment status, and view a skills-passport mock-up.
- **Trade-pack matching:** compare a declaration with the included trade packs and return ranked suggestions, matched and missing outcomes, and possible bridge training. The packs are sample application data, not official qualification standards.
- **Evidence and assessment:** the demonstration page can process live camera frames on-device with MediaPipe face, hand, and pose landmarks; inspect frame brightness and Laplacian blur; run blink/head-turn prompts; and propose work-step timestamps using trade-aware hand-region, posture, and dwell heuristics. Workers can edit suggested timestamps. The video stays in the browser; its SHA-256, timestamp, optional permitted geolocation, quality/liveness metadata, and step record are stored in a server-verified hash chain. These checks are advisory, not certification decisions.
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

The first startup creates the local SQLite database and seeds demo accounts and candidate records. It also adds the evidence-chain columns to existing local SQLite databases.

### 2. Start the frontend

Open a second terminal at the repository root:

```powershell
Set-Location frontend
npm ci
Copy-Item .env.example .env.local
npm run dev -- --host 127.0.0.1 --port 5173
```

Open <http://localhost:5173>. The development client calls the API at `http://localhost:8000`. The example enables the guided tour, passwordless demo-role switcher, and clearly labeled evidence mock fallback; remove `.env.local` or set `VITE_DEMO_MODE=false` to disable the demo-only controls. Set `VITE_EVIDENCE_MOCK_FALLBACK=false` to disable simulated evidence fallback. MediaPipe's JavaScript package is installed locally; its model weights and WebAssembly files are fetched from Google MediaPipe storage and jsDelivr when the camera starts. The camera workflow therefore needs network access for its first model load. To host the model assets locally, change the asset URLs in `frontend/src/api/evidenceVision.ts`.

Set `VITE_API_BASE_URL` in `frontend/.env.local` if the API is running at a different URL. Vite reads these variables at startup, so restart the dev server after changing them.

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
| Moderator / second reviewer | `moderator1` | `moderator123` |
| Worker | `worker1` | `worker123` |

Additional seeded assessor and worker accounts are available as `assessor2` through `assessor8` and `worker2` through `worker60`; the seeded password for each group is the same as shown above. These credentials are public demo credentials and must never be used for real data or an internet-facing deployment.

## One-page demo script (about 8 minutes)

Use only seeded/demo data. Camera permission is optional; if used, the captured video stays in the browser and is not uploaded. Every seeded metric and synthetic subgroup is labeled in the UI.

1. **Start the API and web app** using the local run steps above, then open <http://localhost:5173>. Sign in as `worker1` (`worker123`) or use the demo role switcher when `VITE_DEMO_MODE=true`.
2. **Create a worker journey:** open **Declare skills**, submit a short electrician skills statement, then open **Demonstrate**. Optionally grant camera permission, record a brief clip, and review the on-device quality/liveness readouts. Simulated fallback controls are explicitly labeled.
3. **Review evidence tags:** stop the recording; scrub the local video timeline, select a confidence-coloured step segment to jump to it, then accept, edit timestamps for, or reject a suggested tag. Save the evidence to store its hash and step metadata in the server hash chain (not the video bytes).
4. **Show independent scoring:** switch to `assessor1`, score the assessment using the queue/current assessment ID, and—if selected for second review—switch to the assigned second assessor. A large disagreement routes the case to `moderator1` for a rationale and final scores. Sampling and reviewer availability can affect whether a second review is assigned.
5. **Show calibration and impact:** visit **Calibration** for agreement, drift, and coaching analytics; visit **Impact dashboard** for the stage funnel, timing, trade pass-rate proxy, and subgroup views. The impact “pass” rule and seeded demographics are demonstration-only; these charts are not official outcomes or a fairness audit.
6. **Issue and verify a credential:** after sign-off, switch to an assessor/admin, open `/certificate`, use the assessment ID, and issue/check the signed demo credential. The QR points to the local `/verify/:id` page. The Verified badge requires the demo Ed25519 signature, credential hash, assessment status, and evidence-chain checks to pass. Download the PDF if desired.
7. **Demonstrate tamper detection (admin only):** open **Admin / Packs**, choose **Simulate tampering**, then **Verify chain**. The tool creates and alters a clearly marked synthetic record, leaving a broken link for the verifier to identify. This changes local demo state until reset.
8. **Restore a clean demo:** run `.\scripts\reset_demo.ps1` from the repository root, or from an authenticated administrator call `POST /api/admin/demo-reset`. The Python command is `python scripts/reset_demo.py` (activate `backend\.venv` first if needed). Reset deletes records in the configured demo database, restores the sample trade packs, and reseeds the users, candidates, assessments, and scores.

The reset is destructive to all records in the selected demo database; back up any data you need before running it. Do not run it against a database containing real or shared data.

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
| Second review and moderation | `/moderation` | Compare blind assessor scores and record a moderation decision |
| Trade-pack editor | `/admin/packs` | Validate and save the demo trade-pack registry |
| Calibration | `/calibration` | View persisted-score agreement, drift, and coaching summaries |
| Certificate | `/certificate` | View the certificate demonstration |
| Credential verification | `/verify/:id` | Open the public verification view for an assessment |

## Assessment lifecycle

The backend models the following states:

```text
Registered → Declared → Evidence captured → Under review
           → Second review / Moderation (when applicable)
           → Signed off → Credential issued → Appeal (if needed)
```

On the first assessor score, the API selects approximately 20% of assessments for an independent second review. Set `SECOND_REVIEW_SAMPLE_RATE` to a fraction from `0` to `1` to configure sampling. Assessments flagged by evidence quality or with AI confidence below `0.65` are always assigned a second assessor, regardless of the sampling result. Reviewers are selected from a different centre and cannot be the primary assessor.

The current AI draft is a server-side advisory heuristic (score 3 for quality-flagged evidence, otherwise 4; confidence 0.55 or 0.8 respectively), not a trained model prediction. Clients cannot submit or read it before submitting their own competency score. Each reviewer sees only their own scores during independent review. When both sets are complete, a difference of 2 or more points on any competency sends the assessment to moderation. Moderators can then view both rounds and the AI draft, enter final scores and a rationale, and give a reason for every score changed from either assessor. Score records, overrides, reviewer assignment, moderation decisions, workflow transitions, and audit events are persisted.

## Calibration analytics

The calibration dashboard calculates its metrics from persisted `ScoreRecord` rows; it no longer uses a separate hardcoded chart dataset. On a fresh demo database, startup adds 60 historical demo assessments, eight assessors with different scoring severities, mixed AI-assisted/unassisted scores, and deliberate late-period drift observations. The records use the same score-record creation path as ordinary scoring and are tagged `is_demo`; startup seeding is idempotent. Charts and reports disclose when figures are seeded demo data.

| Dashboard view | Calculation |
| --- | --- |
| Ordinal agreement | Krippendorff's ordinal alpha, with a deterministic assessment-item bootstrap percentile 95% confidence interval |
| Pairwise agreement | Mean quadratic weighted Cohen's kappa across assessor pairs on their common assessment-competency items; weights use the fixed 1-to-5 rubric |
| Absolute agreement | ICC(2,1), two-way random-effects absolute agreement, on complete matched items, with an item-bootstrap interval |
| Assessor severity | Item-adjusted mean residual approximation (positive means stricter than peers); this is explicitly **not** an ordinal-logistic or many-facet Rasch fit |
| Drift and scoring patterns | Monthly score movement from each assessor's first observed month, severity/leniency, and score-range concentration; ±0.5 points is the displayed drift alert threshold |
| Assisted comparison | Descriptive mean absolute peer-consensus difference, grouped by the stored `ai_assisted` flag; this is not a causal A/B estimate |

Assessors can view only their own private coaching report and anchor recommendations; administrators can view the aggregate coaching cards. Anchor recommendations rank consensus score records and are references for coaching, not actual video clips. Metrics are omitted where there are too few overlapping ratings. Seeded measurements are synthetic test/demo data and must not be interpreted as field validation.

## API overview

FastAPI provides the full request and response schemas in `/docs`. The main endpoint groups include:

| Area | Example endpoints |
| --- | --- |
| Health and authentication | `GET /health`, `POST /api/auth/login`, `GET /api/me` |
| Dashboard counters | `GET /api/dashboard` |
| Impact dashboard | `GET /api/dashboard/impact` |
| Competencies and trade packs | `GET /api/competencies`, `GET /api/trade-packs`, `POST /api/trade-packs/validate` |
| Worker declaration and evidence | `POST /api/declare`, `POST /api/assessments`, `POST /api/evidence` |
| Evidence chain | `POST /api/evidence/verify-chain` |
| Tamper demonstration / reset | `POST /api/evidence/simulate-tampering`, `POST /api/admin/demo-reset` |
| Assessor workflow | `GET /api/reviews/queue`, `GET /api/assessments/{id}/review`, `POST /api/score` |
| Moderation | `GET /api/moderation/queue`, `POST /api/moderation` |
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

### Browser end-to-end workflow

From `frontend`, run `npm run test:e2e`. The Playwright configuration starts an isolated in-memory backend on port `8001` and a Vite server on port `5175`; Python backend dependencies must be available to `python`, and Chromium must be installed with `npx playwright install chromium`. The browser test creates flagged evidence, scores it as two different assessors, verifies the blind-review handoff, and saves the moderator’s final rationale and scores.

### Frontend tests, build, and lint

From the repository root:

```powershell
Set-Location frontend
npm ci
npm test
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
- **Calibration demo records:** a fresh local database receives synthetic, explicitly tagged assessor scores for demonstrating the stored-record metrics. They are not measured field results or a causal study; delete the local demo database and seed real, appropriately consented assessment data before evaluating the dashboard.
- **Real versus simulated evidence features:** when models load, face/hand/pose landmarks and brightness/blur/face-in-frame checks run against the live camera in the browser. The liveness prompts inspect a blink or relative face-landmark movement, and work-step timestamps are heuristic proposals. This is not robust anti-spoofing, identity verification, certified liveness, or occupational assessment. Models are downloaded from Google MediaPipe model storage and jsDelivr; camera use requires permission and a secure context. Video bytes and landmark frames are not uploaded; the API receives the client-computed video hash and metadata. Location is optional and requested only on evidence save. If `VITE_EVIDENCE_MOCK_FALLBACK=true`, fallback interactions are explicitly marked simulated and must not be treated as measured results. Turn it off for real-only operation.
- **Heuristic matching:** lexical matching and optional sentence embeddings are not a certified occupational benchmark.
- **Mock integrations and credentials:** the certificate page checks a real Ed25519 signature and hash for the locally generated demo credential, but the issuer key and public verification are local demonstration infrastructure, not an accredited or production trust service. Revocations, notifications, and external delivery behavior remain interface demonstrations.
- **Impact and fairness views:** time comparisons, pass-rate proxies, seeded demographic categories, and subgroup rates are descriptive demonstration outputs. They are not official qualification decisions, causal estimates, or validated fairness assessments.
- **Limited offline behavior:** the app shell can be installed and selected worker actions can be queued locally. API-dependent workflows still need a reachable backend; queue behavior is not a guarantee of complete offline operation or conflict-free synchronization.
- **Development security defaults:** the backend uses demo secrets and permissive local CORS configuration. Authentication, key management, authorization, privacy, retention, transport security, and deployment configuration need a production security review before any real-user use.

Do not submit real personal, assessment, credential, or other sensitive data to this prototype.

Evidence chain verification can be run by an authenticated worker, assessor, moderator, or administrator:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/evidence/verify-chain `
  -Headers @{ Authorization = "Bearer <access-token>" }
```

The API response reports whether every saved chain link verifies. It detects changed proof metadata, changed hashes, and broken links; it does not prove that a camera capture depicts a real person or authentic work.

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
