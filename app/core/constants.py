import enum
from typing import List


class QualificationCategory(str, enum.Enum):
    SSC = "10TH"
    INTERMEDIATE = "INTER"
    UNDERGRADUATE = "UG"
    POSTGRADUATE = "PG"
    DIPLOMA = "DIPLOMA"
    ITI = "ITI"
    OTHER = "OTHER"


NTR_MANDALS: List[str] = [
    "Vijayawada Urban",
    "Vijayawada Rural",
    "Ibrahimpatnam",
    "Mylavaram",
    "Nandigama",
    "Jaggaiahpet",
    "Jaggayyapeta",
    "Tiruvuru",
    "Kanchikacherla",
    "Chandarlapadu",
    "Veerullapadu",
    "G.Konduru",
    "A.Konduru",
    "Reddigudem",
    "Vissannapeta",
    "Penuganchiprolu",
    "Vatsavai",
]

REFERENCE_ADMINS: List[str] = [
    "Direct Student Self-Registration",
    "Admin User (State Operations)",
    "Super Admin (Directorate of Employment)",
    "District Nodal Officer (Vijayawada)",
    "Mandal Placement Officer (Ibrahimpatnam)",
    "Mylavaram Field Counselor",
    "Nandigama Skill Coordinator",
    "Tiruvuru Employment Desk",
]

DISTRICT_LOCATIONS: List[str] = [
    "NTR District",
    "NTR",
    "NTR District (Vijayawada)",
    "Vijayawada",
    "Alluri Sitharama Raju",
    "Anakapalli",
    "Ananthapuramu",
    "Annamayya",
    "Bapatla",
    "Chittoor",
    "Dr. B.R. Ambedkar Konaseema",
    "East Godavari",
    "Eluru",
    "Guntur",
    "Kakinada",
    "Krishna",
    "Kurnool",
    "Nandyal",
    "Palnadu",
    "Parvathipuram Manyam",
    "Prakasam",
    "Sri Potti Sriramulu Nellore",
    "Sri Sathya Sai",
    "Srikakulam",
    "Tirupati",
    "Visakhapatnam",
    "Vizianagaram",
    "West Godavari",
    "Y.S.R. Kadapa",
]


class RecruiterStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


RECRUITER_INDUSTRIES: List[str] = [
    "Information Technology",
    "E-Commerce & Retail",
    "Fintech & Banking",
    "Healthcare & Pharma",
    "EdTech & Education",
    "Logistics & Supply Chain",
    "Automotive & EV",
    "Media & Entertainment",
]

RECRUITER_COMPANY_SIZES: List[str] = [
    "1-10 employees (Startup)",
    "11-50 employees (Small)",
    "51-200 employees (Mid-sized)",
    "201-1000 employees (Large)",
    "1000+ employees (Enterprise)",
]

APPROVED_HEADQUARTERS_CITIES: List[str] = [
    "Alluri Sitharama Raju",
    "Anakapalli",
    "Ananthapuramu",
    "Annamayya",
    "Bapatla",
    "Chittoor",
    "Dr. B.R. Ambedkar Konaseema",
    "East Godavari",
    "Eluru",
    "Guntur",
    "Kakinada",
    "Krishna",
    "Kurnool",
    "Nandyal",
    "NTR",
    "Palnadu",
    "Parvathipuram Manyam",
    "Prakasam",
    "Sri Potti Sriramulu Nellore",
    "Sri Sathya Sai",
    "Srikakulam",
    "Tirupati",
    "Visakhapatnam",
    "Vizianagaram",
    "West Godavari",
    "Y.S.R. Kadapa",
]

