from passlib.context import CryptContext

from .trade_packs import DEFAULT_TRADE_PACKS

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

ASSESSOR_NAMES = [
    "Priya Nair",
    "Rahul Verma",
    "Anjali Singh",
    "Sandeep Rao",
    "Meera Joshi",
    "Nitin Shah",
    "Hema Iyer",
    "Arjun Pillai",
]

WORKER_NAMES = [
    "Amit Kumar", "Sonia Devi", "Ravi Sharma", "Pooja Yadav", "Vikas Reddy", "Nisha Patel",
    "Rahim Ansari", "Kavita Singh", "Deepak Sahu", "Sunita Das", "Gopal Yadav", "Anita Mishra",
    "Harish Verma", "Seema Gupta", "Vinod Meena", "Babita Sen", "Mohan Lal", "Ritika Tiwari",
    "Javed Khan", "Neha Sharma", "Dinesh Kumar", "Pallavi Rao", "Suresh Patil", "Sheetal Kale",
    "Ashok Kumar", "Mitali Roy", "Prakash Nair", "Sarita Pawar", "Rajesh Jadhav", "Uma Reddy",
    "Imran Ali", "Shalini Khanna", "Manoj Tiwari", "Chandni Arora", "Pankaj Saini", "Renu Batra",
    "Madan Singh", "Anjali Rao", "Vivek Pandey", "Nirmala Nair", "Farhan Qureshi", "Kushal Shetty",
    "Asha Singh", "Rajan Iyer", "Tara Bhosale", "Bharat Wagh", "Jiya Shah", "Naveen Kumar",
    "Punit Joshi", "Sarika Dubey", "Kiran More", "Suman Ghosh", "Devendra Mishra", "Monica Sen",
    "Vishal Patel", "Sneha Malhotra", "Rakesh Yadav", "Leela Rani", "Shubham Jain", "Rohit Sharma",
]

DEMO_CANDIDATE_CATALOG = [
    ("worker1", "Domestic Electrician", "Delhi", "+91-98xxxxxx01"),
    ("worker2", "Domestic Electrician", "Lucknow", "+91-98xxxxxx02"),
    ("worker3", "Domestic Electrician", "Jaipur", "+91-98xxxxxx03"),
    ("worker4", "Domestic Electrician", "Bhopal", "+91-98xxxxxx04"),
    ("worker5", "Domestic Electrician", "Patna", "+91-98xxxxxx05"),
    ("worker6", "Domestic Electrician", "Nagpur", "+91-98xxxxxx06"),
    ("worker7", "Domestic Electrician", "Agra", "+91-98xxxxxx07"),
    ("worker8", "Domestic Electrician", "Kanpur", "+91-98xxxxxx08"),
    ("worker9", "Domestic Electrician", "Guwahati", "+91-98xxxxxx09"),
    ("worker10", "Domestic Electrician", "Pune", "+91-98xxxxxx10"),
    ("worker11", "Plumber (General)", "Delhi", "+91-98xxxxxx11"),
    ("worker12", "Plumber (General)", "Lucknow", "+91-98xxxxxx12"),
    ("worker13", "Plumber (General)", "Jaipur", "+91-98xxxxxx13"),
    ("worker14", "Plumber (General)", "Bhopal", "+91-98xxxxxx14"),
    ("worker15", "Plumber (General)", "Patna", "+91-98xxxxxx15"),
    ("worker16", "Plumber (General)", "Nagpur", "+91-98xxxxxx16"),
    ("worker17", "Plumber (General)", "Agra", "+91-98xxxxxx17"),
    ("worker18", "Plumber (General)", "Kanpur", "+91-98xxxxxx18"),
    ("worker19", "Plumber (General)", "Guwahati", "+91-98xxxxxx19"),
    ("worker20", "Plumber (General)", "Pune", "+91-98xxxxxx20"),
    ("worker21", "Mason", "Delhi", "+91-98xxxxxx21"),
    ("worker22", "Mason", "Lucknow", "+91-98xxxxxx22"),
    ("worker23", "Mason", "Jaipur", "+91-98xxxxxx23"),
    ("worker24", "Mason", "Bhopal", "+91-98xxxxxx24"),
    ("worker25", "Mason", "Patna", "+91-98xxxxxx25"),
    ("worker26", "Mason", "Nagpur", "+91-98xxxxxx26"),
    ("worker27", "Mason", "Agra", "+91-98xxxxxx27"),
    ("worker28", "Mason", "Kanpur", "+91-98xxxxxx28"),
    ("worker29", "Mason", "Guwahati", "+91-98xxxxxx29"),
    ("worker30", "Mason", "Pune", "+91-98xxxxxx30"),
    ("worker31", "Tailor / Sewing Machine Operator", "Delhi", "+91-98xxxxxx31"),
    ("worker32", "Tailor / Sewing Machine Operator", "Lucknow", "+91-98xxxxxx32"),
    ("worker33", "Tailor / Sewing Machine Operator", "Jaipur", "+91-98xxxxxx33"),
    ("worker34", "Tailor / Sewing Machine Operator", "Bhopal", "+91-98xxxxxx34"),
    ("worker35", "Tailor / Sewing Machine Operator", "Patna", "+91-98xxxxxx35"),
    ("worker36", "Tailor / Sewing Machine Operator", "Nagpur", "+91-98xxxxxx36"),
    ("worker37", "Tailor / Sewing Machine Operator", "Agra", "+91-98xxxxxx37"),
    ("worker38", "Tailor / Sewing Machine Operator", "Kanpur", "+91-98xxxxxx38"),
    ("worker39", "Tailor / Sewing Machine Operator", "Guwahati", "+91-98xxxxxx39"),
    ("worker40", "Tailor / Sewing Machine Operator", "Pune", "+91-98xxxxxx40"),
    ("worker41", "Domestic Data Entry Operator", "Delhi", "+91-98xxxxxx41"),
    ("worker42", "Domestic Data Entry Operator", "Lucknow", "+91-98xxxxxx42"),
    ("worker43", "Domestic Data Entry Operator", "Jaipur", "+91-98xxxxxx43"),
    ("worker44", "Domestic Data Entry Operator", "Bhopal", "+91-98xxxxxx44"),
    ("worker45", "Domestic Data Entry Operator", "Patna", "+91-98xxxxxx45"),
    ("worker46", "Domestic Data Entry Operator", "Nagpur", "+91-98xxxxxx46"),
    ("worker47", "Domestic Data Entry Operator", "Agra", "+91-98xxxxxx47"),
    ("worker48", "Domestic Data Entry Operator", "Kanpur", "+91-98xxxxxx48"),
    ("worker49", "Domestic Data Entry Operator", "Guwahati", "+91-98xxxxxx49"),
    ("worker50", "Domestic Data Entry Operator", "Pune", "+91-98xxxxxx50"),
    ("worker51", "Domestic Electrician", "Hyderabad", "+91-98xxxxxx51"),
    ("worker52", "Plumber (General)", "Bengaluru", "+91-98xxxxxx52"),
    ("worker53", "Mason", "Chennai", "+91-98xxxxxx53"),
    ("worker54", "Tailor / Sewing Machine Operator", "Coimbatore", "+91-98xxxxxx54"),
    ("worker55", "Domestic Data Entry Operator", "Thiruvananthapuram", "+91-98xxxxxx55"),
    ("worker56", "Domestic Electrician", "Ahmedabad", "+91-98xxxxxx56"),
    ("worker57", "Plumber (General)", "Vadodara", "+91-98xxxxxx57"),
    ("worker58", "Mason", "Indore", "+91-98xxxxxx58"),
    ("worker59", "Tailor / Sewing Machine Operator", "Bhubaneswar", "+91-98xxxxxx59"),
    ("worker60", "Domestic Data Entry Operator", "Ranchi", "+91-98xxxxxx60"),
]

USERS = [
    {"username": "admin", "password": "admin123", "role": "admin", "full_name": "System Admin"},
    *[
        {"username": f"assessor{index}", "password": "assessor123", "role": "assessor", "full_name": assessor_name}
        for index, assessor_name in enumerate(ASSESSOR_NAMES, start=1)
    ],
    *[
        {"username": f"worker{index}", "password": "worker123", "role": "worker", "full_name": worker_name}
        for index, worker_name in enumerate(WORKER_NAMES, start=1)
    ],
]

QUALIFICATION_PACKS = DEFAULT_TRADE_PACKS

COMPETENCIES = [
    {
        "id": "safety-practices",
        "title": "Safety Practices",
        "rubric": {
            "1": "Does not isolate, lacks PPE and hazard identification.",
            "2": "Uses PPE sometimes; isolation steps are incomplete or inconsistent.",
            "3": "Follows basic safety steps with occasional reminders.",
            "4": "Consistently isolates, checks grounding, and follows safe workflow.",
            "5": "Demonstrates strong safety discipline, identifies hidden risks, and leads safe work practice."
        },
        "checklist": [
            "Verify site isolation and risk assessment",
            "Wear required PPE and check tools",
            "Inspect cables, points and environment for hazards",
            "Confirm lockout/tagout or safe switching",
            "Document hazards and remedial actions"
        ],
    },
    {
        "id": "wiring-and-fitting",
        "title": "Wiring and Fitting",
        "rubric": {
            "1": "Routing and termination are unsafe, loose, or inaccurate.",
            "2": "Basic wiring is visible but alignment and fixation need improvement.",
            "3": "Produces acceptable installation with minor quality issues.",
            "4": "Installs neatly with secure fixings and correct connection sequencing.",
            "5": "Delivers high-quality, durable fit-out with clean routing and neat finishing."
        },
        "checklist": [
            "Measure route and plan cable paths",
            "Fix conduits or casing securely",
            "Terminate conductors correctly and label them",
            "Install switchboard/fixtures in alignment",
            "Check for secure fitting before testing"
        ],
    },
    {
        "id": "testing-and-fault-finding",
        "title": "Testing and Fault Finding",
        "rubric": {
            "1": "Cannot test or diagnose basic faults reliably.",
            "2": "Performs basic tests with limited interpretation.",
            "3": "Conducts continuity and insulation checks with moderate accuracy.",
            "4": "Diagnoses common faults using structured testing methods.",
            "5": "Analyses faults accurately, validates corrections, and records findings clearly."
        },
        "checklist": [
            "Inspect circuit before switching on",
            "Perform continuity and insulation tests",
            "Use tester to verify polarity and voltage",
            "Diagnose likely fault and isolate root cause",
            "Record final verification and corrective actions"
        ],
    },
    {
        "id": "tools-handling",
        "title": "Tools Handling",
        "rubric": {
            "1": "Uses tools unsafely or without proper selection.",
            "2": "Uses common tools but needs close supervision.",
            "3": "Selects and uses tools appropriately for normal tasks.",
            "4": "Uses tools efficiently and with safe technique.",
            "5": "Manages toolset and maintenance professionally, minimizing waste and risk."
        },
        "checklist": [
            "Select correct tool for task and rating",
            "Check tool condition before use",
            "Use tools with safe grip and posture",
            "Store tools and accessories properly",
            "Report damaged tools and maintain clean work area"
        ],
    },
    {
        "id": "housekeeping",
        "title": "Housekeeping and Workmanship",
        "rubric": {
            "1": "Leaves clutter and unsafe conditions behind.",
            "2": "Shows basic cleanup but misses several quality points.",
            "3": "Maintains acceptable site cleanliness and order.",
            "4": "Keeps environment tidy and records waste/material management.",
            "5": "Consistently demonstrates disciplined housekeeping and professional workmanship."
        },
        "checklist": [
            "Keep working area clear and hazard-free",
            "Store leftover materials and scrap correctly",
            "Check final finish and alignment",
            "Document completion of housekeeping tasks",
            "Close worksite and prepare handover note"
        ],
    },
]

SAMPLE_DEMO_VIDEOS = [
    {"id": "clip-01", "title": "Safety check at switchboard", "duration": 21},
    {"id": "clip-02", "title": "Cable routing in kitchen circuit", "duration": 27},
    {"id": "clip-03", "title": "Earth continuity testing", "duration": 19},
    {"id": "clip-04", "title": "Fault diagnosis in lighting loop", "duration": 31},
    {"id": "clip-05", "title": "Final housekeeping and signage", "duration": 18},
]

def password_hash(password: str) -> str:
    return pwd_context.hash(password)
