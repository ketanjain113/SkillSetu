# SkillSetu AI

SkillSetu AI is an offline-first PWA prototype for AI-assisted Recognition of Prior Learning (RPL) assessment. The platform supports worker declaration, guided evidence capture, assessor review, and hash-verified certificate issuance while keeping the AI advisory-only and requiring a human sign-off.

## Overview

- Frontend: React + Vite + TypeScript + PWA service worker and manifest
- Offline store: IndexedDB / Dexie with queued writes and background sync
- Backend: FastAPI + SQLAlchemy + SQLite, JWT auth, role-based access control
- AI behavior: advisory only, explicitly labelled as Demo data / AI suggested; never auto-certifies
- Demo accounts: admin, assessor1, assessor2, assessor3, worker1-6
- Current milestone: Worker experience, multilingual access, accessibility controls, and demo notifications

## Quick start

### Option 1: local development

1. From the repository root, install the backend dependencies and start the API (PowerShell):

   ```powershell
   python -m venv backend\.venv
   .\backend\.venv\Scripts\Activate.ps1
   pip install -r backend\requirements-dev.txt
   $env:PYTHONPATH = 'backend'
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

   `requirements.txt` contains runtime packages; `requirements-dev.txt` adds test and development tools.
2. In a separate terminal, install frontend dependencies and start Vite:

   ```powershell
   cd frontend
   npm ci
   npm run dev -- --host 0.0.0.0 --port 5173
   ```
3. Open http://localhost:5173

Seed demo data from the repository root when needed:

```powershell
$env:PYTHONPATH = 'backend'
python scripts\seed_demo.py
```

Demo users:
- admin / admin123
- assessor1 / assessor123
- worker1 / worker123

### Option 2: Docker

```bash
docker compose up --build
```

Then open:
- Frontend: http://localhost:5173
- API: http://localhost:8000/docs

### Reset demo state

```bash
python scripts\reset_demo.py
```

---

## Milestone 1: multi-trade, data-driven engine

This milestone adds a versioned trade-pack registry and keeps the existing Phase 1 flow intact. The app now uses a pack-driven declaration engine instead of a single hard-coded trade description.

Included pack set:
- Domestic Electrician
- Plumber (General)
- Mason
- Tailor / Sewing Machine Operator
- Domestic Data Entry Operator

Each trade pack includes:
- QP code and NSQF level
- 5–6 NOS entries
- rubric anchors (1–5)
- 6–10 checklist items
- safety-critical steps
- pass threshold
- pack version

### Safety-critical cap rule

If a safety-critical step fails, the overall result is capped at “Not yet competent” regardless of the average rubric score. This is enforced in the pack evaluation layer and is presented to the assessor as a hard safety rule, not a suggestion.

### Admin pack editor

The admin view at /admin/packs allows the authorized admin to edit the JSON trade pack registry and save it with the backend schema validator. The pack version is then included in the credential response and stored with the pack match metadata.

### QP matching

The declaration engine combines:
- lexical matching
- sentence-embedding similarity when available
- NSQF rule-prerequisite graph logic

It returns the top 3 ranked pack matches with:
- confidence score
- matched NOS
- missing NOS
- suggested bridge-training list
- pack version and NSQF level

---

## Milestone 3: workflow lifecycle and review roles

This milestone adds a server-enforced assessment lifecycle that follows the human-led RPL review model:

Registered → Declared → Evidence captured → Under review → Second review (if sampled or flagged) → Moderation (if disagreement) → Signed off → Credential issued → Appeal

The workflow is enforced server-side and surfaced to the worker through a status tracker. Valid transitions are restricted at the API layer, so a state can only move through approved review paths rather than skipping directly to a later stage.

Roles and review gates include:
- worker: declaration, evidence submission, status tracking
- assessor: scoring and first review
- moderator / lead assessor: moderation and disagreement handling
- RPL centre admin: operational assignment and audit visibility
- SSC / state admin: higher-level oversight and verification reporting
- auditor: audit-log review and compliance checking

Human decision-making remains central: AI remains advisory-only, every override requires a typed reason, and all override decisions go into the audit trail before a credential is issued.

---

## Milestone 4: calibration engine 2.0

This milestone adds a stronger calibration layer for assessor quality and AI explainability, while remaining explicitly demo-only unless real pilot data is available.

Included components:
- ordinal Krippendorff's alpha with confidence intervals
- weighted Cohen's kappa and ICC summaries
- many-facet ordinal approximation for assessor severity, candidate ability and item difficulty
- private coaching report cards for each assessor
- anchor-clip exam generation for recertification and drift monitoring
- drift alerts for lead assessors with a configurable threshold
- A/B study summary for assisted vs unassisted scoring, with clearly flagged demo data
- explainability panel for AI draft scoring, including confidence gating and refusal when low confidence

All calibration values are presented as pilot or demo metrics unless the project is connected to real assessor data. The UI clearly labels demo-only values and the README keeps a known-limitations note for all synthetic outputs.

---

## Milestone 5: worker experience and access

This milestone adds the worker-facing access layer needed for low-bandwidth, multilingual, and accessibility-first RPL use in field conditions.

Included changes:
- multilingual worker UI across English, Hindi, Marathi, Tamil and Bengali via locale-driven text resources
- speech prompt playback and microphone capture using the browser speech API with a graceful fallback path
- low-literacy mode with large action buttons, icon-led task flow, and simple single-action screens
- accessibility polish with stronger contrast, keyboard focus states, reduced-motion handling, and screen-reader-friendly labels
- sync queue visibility with offline retry rules and graceful storage-quota fallback messaging
- My Skills Passport page with QR-share mock flow, bridge-course recommendations, and recommended local jobs
- SMS / WhatsApp mock notification provider interfaces that can be swapped for real providers without changing the workflow

All voice, queue, passport, and notification behaviors remain demo-only and are labelled as such in the UI when they are heuristic or synthetic.

---

## Milestone 7: integrations (mocked but realistic)

This milestone adds realistic integration contracts for data exchange and verification without pretending the pilot is already connected to production systems.

Included components:
- Skill India Digital / DigiLocker-style verifiable credential issuance using a W3C-compatible JSON-LD structure and an Ed25519 signature
- public verification endpoint that checks both the signature and the credential hash chain
- revocation list endpoint for demo invalidation of credentials
- NCVET / SSC adapter with push payloads, webhook signatures, retries, and delivery metadata
- certificate and competency-profile PDF export, CSV result export, and API-key-protected integration endpoints
- OpenAPI docs generated automatically by FastAPI for third-party API access

All integration data is clearly mock or pilot-grade and is not presented as a live national system connection.

---

## Demo labels and AI guarantees

The following are explicitly labelled in the product UI and README:

- Demo data / AI suggested labels are shown next to heuristic suggestions.
- The calibration engine values are pilot data only.
- AI output is advisory; it never auto-certifies.
- Assessor overrides require a typed reason and are recorded in the audit log.

---

## Known limitations

This prototype is intentionally honest about what is simulated or heuristic:

- sentence-transformers fallback uses lexical matching if the AI embedding model is unavailable; the UI labels it as Demo data or AI suggested
- the QP matching is a demo heuristic and not a certified occupational benchmarking system
- the video quality checks are heuristic brightness/blur estimates, not a production-grade MediaPipe pipeline
- liveness cues remain a prompt-based pseudo-check rather than a production biometric validation system
- the PDF/QR credential export is a demo artifact
- calibration metrics are seeded pilot numbers for training and validation, not measured assessment results
- the safety cap is a policy guardrail in the prototype and should be confirmed by an assessor in a live pilot
- the voice input path, notification senders, and passport recommendations are demo/mock flows intended for field testing and UX validation, not production-grade telecom or occupational data services

---

## Milestone 8: quality, demo and delivery

This final demo milestone focuses on making the prototype credible in a live review environment without overstating production maturity.

Included quality and delivery work:
- realistic demo seed set with 60 worker candidates across five trade streams and eight assessors
- reset and re-seed scripts for a clean demo refresh before stakeholder walkthroughs
- quality regression checks for the seeded data and the primary assessor workflow
- honest labeling of all synthetic values as demo data, AI suggested, or pilot-grade metrics
- a single-command Docker path for local onboarding and a consistent demo reset flow

### Demo readiness checklist

- Local stack: docker compose up --build
- Reset demo data: python scripts\reset_demo.py
- Re-seed demo data: python scripts\seed_demo.py
- Backend validation: cd backend; python -m pytest -q
- Frontend validation: cd frontend; npm run build

### Quality guardrails

- AI output remains advisory only and never auto-certifies a worker.
- Every override requires a typed reason and is stored in the audit log.
- Seeded calibration results and other synthetic values are flagged as demo or pilot data in the UI and in this README.
- The prototype explicitly separates measured outcomes from pilot-only heuristics.

---

## Tests

Run the backend regression suite:

```bash
cd backend
python -m pytest -q
```

The project includes:
- unit tests for ordinal kappa / alpha calculations
- trade-pack validation and safety-cap regression tests
- worker → assessor → certificate end-to-end flow checks
- hash-chain integrity checks
- demo-seed regression checks for realistic candidate and assessor coverage

---

## Project structure

```text
SkillSetu-AI/
  .gitignore
  backend/
    app/
    tests/
    Dockerfile
    requirements.txt
    requirements-dev.txt
  frontend/
    src/
    public/
    Dockerfile
    package.json
    package-lock.json
    vite.config.ts
  scripts/
    seed_demo.py
    reset_demo.py
  docker-compose.yml
  README.md
```
