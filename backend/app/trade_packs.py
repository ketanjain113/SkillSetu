from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_TRADE_PACKS: List[Dict[str, Any]] = [
    {
        "pack_id": "domestic-electrician",
        "title": "Domestic Electrician",
        "trade_code": "ELE-NSQF-4",
        "nsqf_level": 4,
        "summary": "Residential wiring, safety checks, earthing, testing, and fault isolation for domestic electrical installations.",
        "keywords": [
            "domestic electrician", "wiring", "switchboard", "earthing", "lighting",
            "continuity", "insulation", "safety", "cabling", "fault finding", "circuit"
        ],
        "pass_threshold": 0.7,
        "version": "2026.1.0",
        "safety_critical_steps": [
            "Isolate/lock out and verify power is off before work.",
            "Check PPE and tool condition before starting work.",
            "Confirm earthing and earth continuity before energising."
        ],
        "rubric": {
            "1": "Unsafe or incomplete work with poor safety and diagnosis.",
            "2": "Basic task completion with inconsistent safety and quality control.",
            "3": "Competent in routine domestic wiring and safe testing.",
            "4": "Reliable and safe execution with accurate fault identification.",
            "5": "Highly consistent, safe, and professional quality across tasks."
        },
        "checklist": [
            "Conduct a site safety and risk review",
            "Wear PPE and inspect tools before starting",
            "Measure route and decide cable path",
            "Install or fix wiring, conduits, and fittings",
            "Test continuity, insulation, and earthing",
            "Diagnose common faults and re-test after correction",
            "Verify final switchboard and fixture alignment",
            "Record final checks and housekeeping details"
        ],
        "nos": [
            {
                "id": "DE-NOS-01",
                "title": "Plan and prepare work area",
                "description": "Assess site, identify hazards, prepare tools and PPE.",
                "keywords": ["safety", "risk", "site", "ppe", "tools"],
                "prerequisites": []
            },
            {
                "id": "DE-NOS-02",
                "title": "Install domestic wiring and fixtures",
                "description": "Fix cables, conduit, switchboards, and light points.",
                "keywords": ["wiring", "fixture", "switchboard", "cable", "conduit"],
                "prerequisites": ["DE-NOS-01"]
            },
            {
                "id": "DE-NOS-03",
                "title": "Perform earthing and continuity checks",
                "description": "Verify earth continuity, polarity, and circuit integrity.",
                "keywords": ["earthing", "continuity", "insulation", "polarity", "testing"],
                "prerequisites": ["DE-NOS-02"]
            },
            {
                "id": "DE-NOS-04",
                "title": "Diagnose basic faults and repair",
                "description": "Isolate faults in lighting, sockets, and branches.",
                "keywords": ["fault", "repair", "diagnose", "circuit", "troubleshoot"],
                "prerequisites": ["DE-NOS-03"]
            },
            {
                "id": "DE-NOS-05",
                "title": "Complete final inspection and handover",
                "description": "Document safe completion and work quality checks.",
                "keywords": ["handover", "inspection", "housekeeping", "documentation"],
                "prerequisites": ["DE-NOS-04"]
            }
        ]
    },
    {
        "pack_id": "plumber-general",
        "title": "Plumber (General)",
        "trade_code": "PLM-NSQF-3",
        "nsqf_level": 3,
        "summary": "Water supply, drainage, fixture installation, pipe fitting, and safe plumbing operations.",
        "keywords": [
            "plumber", "pipe", "water supply", "sanitary", "fitting", "drainage", "valve",
            "jointing", "leak", "fixture", "pressure", "pipe routing"
        ],
        "pass_threshold": 0.68,
        "version": "2026.1.0",
        "safety_critical_steps": [
            "Check pressure and isolate supply before cutting or fitting.",
            "Use correct PPE and confirm tool condition.",
            "Verify leak-free joints and pressure testing before closure."
        ],
        "rubric": {
            "1": "Pipes and joints are not compliant or leak-prone.",
            "2": "Basic fitting attempts are incomplete or uneven.",
            "3": "Routine pipe work is installed with acceptable quality.",
            "4": "Strong pipe routing and dependable joint integrity.",
            "5": "Skilled, neat, and durable plumbing work with safe testing."
        },
        "checklist": [
            "Check water supply and isolate the line",
            "Measure pipe route and select correct fitting",
            "Cut, prepare, and fix piping securely",
            "Join pipe sections with correct sealing method",
            "Install sanitary fittings and valves",
            "Leak test under working pressure",
            "Check final alignment and drainage flow",
            "Document final quality and housekeeping"
        ],
        "nos": [
            {"id": "PL-NOS-01", "title": "Prepare plumbing work area", "description": "Inspect pressure, layout, and hygiene conditions.", "keywords": ["pressure", "site", "supply", "safety"], "prerequisites": []},
            {"id": "PL-NOS-02", "title": "Measure and route piping", "description": "Plan pipe alignment and fitting locations.", "keywords": ["measure", "routing", "pipe", "layout"], "prerequisites": ["PL-NOS-01"]},
            {"id": "PL-NOS-03", "title": "Install pipe joints and fittings", "description": "Fix and seal pipe segments for service integrity.", "keywords": ["joint", "fitting", "seal", "pipe"], "prerequisites": ["PL-NOS-02"]},
            {"id": "PL-NOS-04", "title": "Install sanitary fixtures and valves", "description": "Mount valves, taps, and sanitary fittings correctly.", "keywords": ["valve", "tap", "fixture", "sanitary"], "prerequisites": ["PL-NOS-03"]},
            {"id": "PL-NOS-05", "title": "Test for leaks and completion", "description": "Conduct pressure checks and final handover.", "keywords": ["pressure", "leak", "test", "handover"], "prerequisites": ["PL-NOS-04"]}
        ]
    },
    {
        "pack_id": "mason",
        "title": "Mason",
        "trade_code": "MAS-NSQF-3",
        "nsqf_level": 3,
        "summary": "Block work, plastering, masonry alignment, and finishing for structural and finishing tasks.",
        "keywords": [
            "mason", "brick", "masonry", "plaster", "wall", "cement", "alignment", "level",
            "blockwork", "finishing", "foundation", "jointing"
        ],
        "pass_threshold": 0.68,
        "version": "2026.1.0",
        "safety_critical_steps": [
            "Check material quality and safe stacking before work.",
            "Wear PPE and confirm working area is stable.",
            "Verify level and alignment before final finishing."
        ],
        "rubric": {
            "1": "Work is uneven, unstable, or unsafe.",
            "2": "Fundamental masonry is inconsistent and needs supervision.",
            "3": "Standard block and plaster tasks are completed with acceptable finish.",
            "4": "Strong alignment, stable structure, and neat finishing.",
            "5": "Professional finish, precision, and consistently durable masonry."
        },
        "checklist": [
            "Assess site and ground conditions",
            "Prepare mortar or mix in the correct proportion",
            "Lay first course with accurate line and level",
            "Build masonry wall or blockwork to specification",
            "Check bond pattern and vertical alignment",
            "Apply plaster or finish by surface requirements",
            "Clean joints and remove excess material",
            "Carry out final inspection and documentation"
        ],
        "nos": [
            {"id": "MS-NOS-01", "title": "Interpret masonry plan and prepare site", "description": "Review layout, safety, and material requirement.", "keywords": ["layout", "site", "safety", "materials"], "prerequisites": []},
            {"id": "MS-NOS-02", "title": "Mix and prepare mortar materials", "description": "Prepare correct mix and tool readiness.", "keywords": ["mix", "mortar", "cement", "water"], "prerequisites": ["MS-NOS-01"]},
            {"id": "MS-NOS-03", "title": "Lay masonry and maintain alignment", "description": "Build walls and check level and bond.", "keywords": ["brick", "block", "alignment", "level"], "prerequisites": ["MS-NOS-02"]},
            {"id": "MS-NOS-04", "title": "Apply plaster and finish surfaces", "description": "Prepare and finish plasters and surfaces.", "keywords": ["plaster", "finish", "surface", "joint"], "prerequisites": ["MS-NOS-03"]},
            {"id": "MS-NOS-05", "title": "Final quality check and handover", "description": "Inspect output and document workmanship.", "keywords": ["inspection", "handover", "quality"], "prerequisites": ["MS-NOS-04"]}
        ]
    },
    {
        "pack_id": "tailor-sewing-machine-operator",
        "title": "Tailor / Sewing Machine Operator",
        "trade_code": "TLM-NSQF-3",
        "nsqf_level": 3,
        "summary": "Fabric measurement, cutting, machine stitching, finishing, and garment quality inspection.",
        "keywords": [
            "tailor", "sewing machine", "fabric", "stitch", "garment", "measurement",
            "cutting", "hem", "machine operator", "finishing", "fitting"
        ],
        "pass_threshold": 0.68,
        "version": "2026.1.0",
        "safety_critical_steps": [
            "Confirm machine guard and needle safety before starting.",
            "Check fabric alignment and sharp tool handling.",
            "Verify seam quality and finish before final handover."
        ],
        "rubric": {
            "1": "Seams and fit are inconsistent and unsafe.",
            "2": "Basic stitching is visible but needs significant correction.",
            "3": "Routine tailoring and machine operation are acceptable.",
            "4": "Good fit, seam consistency, and neat garments.",
            "5": "Professional quality with accurate finishing and strong garment control."
        },
        "checklist": [
            "Check design specification and fabric type",
            "Take measurements and mark pattern accurately",
            "Cut fabric with proper alignment",
            "Set machine and thread to the required stitch",
            "Stitch main seams and finishing details",
            "Check fit, seam strength, and alignment",
            "Press and finish the garment",
            "Inspect final quality and package for handover"
        ],
        "nos": [
            {"id": "TS-NOS-01", "title": "Interpret garment specification", "description": "Understand the design, size, and material requirements.", "keywords": ["specification", "measurement", "fabric"], "prerequisites": []},
            {"id": "TS-NOS-02", "title": "Cut and prepare fabric", "description": "Mark, align, and cut cloth to pattern.", "keywords": ["cutting", "pattern", "fabric"], "prerequisites": ["TS-NOS-01"]},
            {"id": "TS-NOS-03", "title": "Operate machine for stitching", "description": "Manage machine settings and stitch seams accurately.", "keywords": ["stitch", "machine", "seam"], "prerequisites": ["TS-NOS-02"]},
            {"id": "TS-NOS-04", "title": "Finish and press garment", "description": "Perform hems, edging, and garment finishing.", "keywords": ["hem", "finish", "press", "garment"], "prerequisites": ["TS-NOS-03"]},
            {"id": "TS-NOS-05", "title": "Check quality and final package", "description": "Inspect final workmanship and present for handover.", "keywords": ["quality", "inspection", "packaging"], "prerequisites": ["TS-NOS-04"]}
        ]
    },
    {
        "pack_id": "domestic-data-entry-operator",
        "title": "Domestic Data Entry Operator",
        "trade_code": "DDE-NSQF-3",
        "nsqf_level": 3,
        "summary": "Data capture, form entry, validation, file management, and safe digital work practices.",
        "keywords": [
            "data entry", "typing", "form", "spreadsheet", "database", "digitisation",
            "validation", "records", "upload", "computer operator", "digital form"
        ],
        "pass_threshold": 0.68,
        "version": "2026.1.0",
        "safety_critical_steps": [
            "Protect data and verify source document before entry.",
            "Confirm login and workstation safety before use.",
            "Validate output accuracy before final filing or submission."
        ],
        "rubric": {
            "1": "High error rate and poor file discipline.",
            "2": "Basic entry is slow and inconsistent.",
            "3": "Routine data entry is accurate with moderate speed.",
            "4": "Reliable entry, validation, and file handling.",
            "5": "Very accurate, efficient, and disciplined digital records management."
        },
        "checklist": [
            "Verify source document and task instructions",
            "Open correct form, spreadsheet, or database",
            "Enter data accurately in the right fields",
            "Validate duplicate, missing, or inconsistent entries",
            "Correct errors and update the record log",
            "Save file, backup, and secure the document",
            "Review output quality and completion status",
            "Prepare handover or submission notes"
        ],
        "nos": [
            {"id": "DD-NOS-01", "title": "Prepare source document and workstation", "description": "Check forms, files, and machine readiness.", "keywords": ["source", "document", "workstation", "setup"], "prerequisites": []},
            {"id": "DD-NOS-02", "title": "Capture and verify data entry", "description": "Input information accurately and validate fields.", "keywords": ["typing", "entry", "validation", "field"], "prerequisites": ["DD-NOS-01"]},
            {"id": "DD-NOS-03", "title": "Maintain records and file structure", "description": "Organise digital records and keep naming consistent.", "keywords": ["file", "record", "storage", "backup"], "prerequisites": ["DD-NOS-02"]},
            {"id": "DD-NOS-04", "title": "Check for errors and corrections", "description": "Identify and correct mismatches, missing data, or duplicates.", "keywords": ["error", "correction", "duplicate", "validation"], "prerequisites": ["DD-NOS-03"]},
            {"id": "DD-NOS-05", "title": "Submit final records and document completion", "description": "Final quality review and secure handover.", "keywords": ["submission", "handover", "review", "completion"], "prerequisites": ["DD-NOS-04"]}
        ]
    }
]

RULE_GRAPH = {
    "domestic-electrician": [],
    "plumber-general": ["domestic-electrician"],
    "mason": ["domestic-electrician"],
    "tailor-sewing-machine-operator": ["domestic-electrician"],
    "domestic-data-entry-operator": ["domestic-electrician"],
}

PACK_PATH = Path(__file__).with_name("trade_packs_data.json")


def _fallback_pack_store() -> List[Dict[str, Any]]:
    return deepcopy(DEFAULT_TRADE_PACKS)


def load_trade_packs() -> List[Dict[str, Any]]:
    if PACK_PATH.exists():
        try:
            loaded = json.loads(PACK_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, list) and loaded:
                return loaded
        except (json.JSONDecodeError, OSError):
            pass
    return _fallback_pack_store()


CURRENT_TRADE_PACKS = load_trade_packs()


def validate_trade_pack(pack: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    required_fields = ["pack_id", "title", "summary", "keywords", "pass_threshold", "rubric", "checklist", "safety_critical_steps", "nos", "version"]
    for field in required_fields:
        if field not in pack:
            errors.append(f"Missing field: {field}")

    if "pack_id" in pack and not isinstance(pack["pack_id"], str):
        errors.append("pack_id must be a string")
    if "nsqf_level" in pack and not isinstance(pack["nsqf_level"], int):
        errors.append("nsqf_level must be an integer")
    if "pass_threshold" in pack and not isinstance(pack["pass_threshold"], (int, float)):
        errors.append("pass_threshold must be numeric")
    if "checklist" in pack and not isinstance(pack["checklist"], list):
        errors.append("checklist must be a list")
    if "safety_critical_steps" in pack and not isinstance(pack["safety_critical_steps"], list):
        errors.append("safety_critical_steps must be a list")
    if "nos" in pack and (not isinstance(pack["nos"], list) or len(pack["nos"]) < 5):
        errors.append("nos must contain at least 5 items")
    if "rubric" in pack and not isinstance(pack["rubric"], dict):
        errors.append("rubric must be a dictionary")

    if "pass_threshold" in pack and 0 <= float(pack["pass_threshold"]) <= 1:
        pass
    elif "pass_threshold" in pack:
        errors.append("pass_threshold must be between 0 and 1")

    return {"valid": not errors, "errors": errors}


def normalize_trade_pack(pack: Dict[str, Any]) -> Dict[str, Any]:
    normalized = deepcopy(pack)
    normalized.setdefault("keywords", [])
    normalized.setdefault("rubric", {})
    normalized.setdefault("checklist", [])
    normalized.setdefault("safety_critical_steps", [])
    normalized.setdefault("nos", [])
    normalized.setdefault("version", "2026.1.0")
    return normalized


def save_trade_packs(packs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for pack in packs:
        validated = validate_trade_pack(pack)
        if not validated["valid"]:
            raise ValueError("Invalid trade pack: " + "; ".join(validated["errors"]))
        normalized.append(normalize_trade_pack(pack))
    PACK_PATH.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    globals()["CURRENT_TRADE_PACKS"] = normalized
    return normalized


def get_trade_pack_by_id(pack_id: str) -> Dict[str, Any] | None:
    return next((pack for pack in CURRENT_TRADE_PACKS if pack.get("pack_id") == pack_id), None)


def _pack_text(pack: Dict[str, Any]) -> str:
    return " ".join(
        [
            pack.get("title", ""),
            pack.get("summary", ""),
            " ".join(pack.get("keywords", [])),
            " ".join(nos.get("title", "") + " " + nos.get("description", "") for nos in pack.get("nos", [])),
        ]
    )


def lexical_similarity(query: str, candidate: str) -> float:
    query_tokens = set((query.lower().replace("/", " ").replace("-", " ").replace("_", " ").replace("[\n]", " ")).split())
    candidate_tokens = set((candidate.lower().replace("/", " ").replace("-", " ").replace("_", " ").replace("[\n]", " ")).split())
    if not query_tokens and not candidate_tokens:
        return 0.0
    overlap = query_tokens & candidate_tokens
    return len(overlap) / max(len(query_tokens | candidate_tokens), 1)


def match_nos_to_text(pack: Dict[str, Any], text: str) -> Dict[str, List[str]]:
    normalized = text.lower()
    matched = []
    missing = []
    for nos in pack.get("nos", []):
        combined = " ".join([nos.get("title", ""), nos.get("description", ""), " ".join(nos.get("keywords", []))]).lower()
        if any(keyword.lower() in normalized for keyword in [nos.get("title", ""), *nos.get("keywords", [])]) or any(keyword.lower() in combined for keyword in [word for word in normalized.split() if len(word) > 3]):
            matched.append(nos.get("id"))
        else:
            missing.append(nos.get("id"))
    return {"matched": matched, "missing": missing}


def build_bridge_training(pack: Dict[str, Any], missing_nos: List[str]) -> List[str]:
    if not missing_nos:
        return ["Continue supervised practice in core routine work and audit review."]
    names = []
    for nos in pack.get("nos", []):
        if nos.get("id") in missing_nos:
            names.append(nos.get("title", "Unspecified skill area"))
    return names[:3]


def rank_qualification_packs(text: str, packs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = text.lower()
    results: List[Dict[str, Any]] = []
    for pack in packs:
        lexical = lexical_similarity(normalized, _pack_text(pack))
        nsqf_bonus = 0.05 if pack.get("nsqf_level", 1) <= 3 else 0.02
        rule_bonus = 0.0
        for prerequisite in RULE_GRAPH.get(pack.get("pack_id"), []):
            if prerequisite in normalized:
                rule_bonus += 0.03
        confidence = max(0.2, min(0.99, round(0.45 + lexical * 0.55 + nsqf_bonus + rule_bonus, 4)))
        matched = match_nos_to_text(pack, text)
        results.append({
            "pack_id": pack.get("pack_id"),
            "title": pack.get("title"),
            "confidence": confidence,
            "summary": pack.get("summary"),
            "skill_gaps": [
                nos.get("title", "Missing competency") for nos in pack.get("nos", []) if nos.get("id") in matched["missing"]
            ],
            "matched_nos": matched["matched"],
            "missing_nos": matched["missing"],
            "bridge_training": build_bridge_training(pack, matched["missing"]),
            "nsqf_level": pack.get("nsqf_level"),
            "pack_version": pack.get("version"),
            "safety_critical_steps": pack.get("safety_critical_steps", []),
            "pass_threshold": pack.get("pass_threshold", 0.7),
        })
    results.sort(key=lambda item: item["confidence"], reverse=True)
    return results[:3]


def evaluate_pack_outcome(average_score: float, safety_critical_passed: bool, safety_critical_steps: List[str] | None = None, pass_threshold: float = 0.7) -> Dict[str, Any]:
    safety_critical_steps = safety_critical_steps or []
    pass_score = float(pass_threshold) * 5.0
    status = "Competent" if average_score >= pass_score and safety_critical_passed else "Not yet competent"
    safety_cap_applied = (not safety_critical_passed) and bool(safety_critical_steps)
    return {
        "overall_status": status,
        "average_score": float(average_score),
        "pass_score": pass_score,
        "safety_cap_applied": safety_cap_applied,
        "safety_critical_steps": safety_critical_steps,
        "recommendation": "Safety-critical checks must be passed before certification can be considered. This is a human decision, not an automated approval." if safety_cap_applied else "Ready for assessor review.",
    }
