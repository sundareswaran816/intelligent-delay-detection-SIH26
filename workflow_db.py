"""
In-memory Mock Database & Business Logic Engine for Civiora.
Provides state tracking for Services, Applications (Files), Officers,
Razorpay payments, DigiLocker verification, E-Sign records, and Department verifiers.
"""
import json
import time
import hmac
import hashlib
from datetime import datetime
from ai_engine import predict_delay_and_eta

SERVICES_CATALOG = [
    {
        "id": "SRV-PENSION-01",
        "name": "Senior Citizen Family Pension Sanction",
        "department": "PENSION",
        "department_name": "Department of Pension & Pensioners' Welfare",
        "category": "Social Security & Pensions",
        "fee": 50,
        "sla_days": 14,
        "required_documents": [
            {
                "id": "DOC-AADHAAR",
                "name": "Applicant Aadhaar Card / e-KYC",
                "department_verifier": "Unique Identification Authority of India (UIDAI)",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "DigiLocker verified Aadhaar card or clear photo copy."
            },
            {
                "id": "DOC-PPO",
                "name": "Pension Payment Order (PPO) / Succession Certificate",
                "department_verifier": "Central Pension Accounting Office (CPAO)",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 10,
                "instructions": "Original PPO document issued by the principal employer."
            },
            {
                "id": "DOC-BANK",
                "name": "Bank Passbook / Cancelled Cheque (Mandate)",
                "department_verifier": "Public Sector Bank / NPCI Core Banking",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Must show clear IFSC, Account No, and Applicant Name."
            },
            {
                "id": "DOC-PHOTO",
                "name": "Passport Size Photograph & Signature",
                "department_verifier": "DigiLocker Biometric Self-Attestation",
                "mandatory": True,
                "accepted_formats": "JPG, PNG",
                "max_size_mb": 2,
                "instructions": "Recent white-background passport photograph and digital signature."
            }
        ]
    },
    {
        "id": "SRV-REV-02",
        "name": "Agricultural Land Title Deed Mutation",
        "department": "REVENUE",
        "department_name": "Department of Land & Revenue",
        "category": "Land Records & Revenue",
        "fee": 100,
        "sla_days": 10,
        "required_documents": [
            {
                "id": "DOC-AADHAAR",
                "name": "Applicant Aadhaar Card",
                "department_verifier": "UIDAI e-KYC",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Identity proof of buyer / applicant."
            },
            {
                "id": "DOC-DEED",
                "name": "Registered Sale Deed / Partition Deed Copy",
                "department_verifier": "Sub-Registrar Office & Land Records",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 15,
                "instructions": "Certified copy from the Sub-Registrar registry."
            },
            {
                "id": "DOC-ROR",
                "name": "Latest RoR / Patta / 7/12 Extract",
                "department_verifier": "Revenue e-Dharti Portal",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 5,
                "instructions": "Record of Rights extract not older than 3 months."
            },
            {
                "id": "DOC-TAX",
                "name": "Up-to-Date Land Revenue Tax Paid Challan",
                "department_verifier": "State Treasury / e-Challan",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Current financial year tax payment receipt."
            }
        ]
    },
    {
        "id": "SRV-MUN-03",
        "name": "Commercial Water Connection NOC",
        "department": "MUNICIPAL",
        "department_name": "Urban Local Bodies & Civic Affairs",
        "category": "Urban Utilities & NOC",
        "fee": 200,
        "sla_days": 7,
        "required_documents": [
            {
                "id": "DOC-AADHAAR",
                "name": "Proprietor / Authorized Signatory Aadhaar",
                "department_verifier": "UIDAI",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Identity proof of applicant / proprietor."
            },
            {
                "id": "DOC-PROP",
                "name": "Municipal Property Tax Assessment / Holding Receipt",
                "department_verifier": "ULB Property Tax Wing",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Receipt showing assessment for commercial premises."
            },
            {
                "id": "DOC-BLDG",
                "name": "Approved Building Sanction Plan (Site Drawing)",
                "department_verifier": "Town & Country Planning Directorate",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 20,
                "instructions": "Architectural drawing with plumbing inlet marked."
            },
            {
                "id": "DOC-TRADE",
                "name": "Trade License / Fire NOC",
                "department_verifier": "Directorate of Fire & Emergency Services",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 10,
                "instructions": "Current valid fire clearance or civic trade license."
            }
        ]
    },
    {
        "id": "SRV-REV-04",
        "name": "Income & Asset Certificate for EWS / Scholarship",
        "department": "REVENUE",
        "department_name": "Department of Land & Revenue",
        "category": "Certificates & Social Welfare",
        "fee": 30,
        "sla_days": 5,
        "required_documents": [
            {
                "id": "DOC-PAN",
                "name": "Applicant / Father PAN Card",
                "department_verifier": "Income Tax Department (ITD)",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Tax return / Form 16 or PAN card."
            },
            {
                "id": "DOC-SALARY",
                "name": "Employer Salary Slip / Village Income Affidavit",
                "department_verifier": "Revenue Circle Inspector & Tahsildar",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Salary slip or notarized income self-declaration."
            },
            {
                "id": "DOC-RATION",
                "name": "NFSA Digital Ration Card / BPL Proof",
                "department_verifier": "Food & Civil Supplies Department",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Ration card showing family member census list."
            }
        ]
    },
    {
        "id": "SRV-MUN-05",
        "name": "Birth & Domicile Official Certificate",
        "department": "MUNICIPAL",
        "department_name": "Urban Local Bodies & Civic Affairs",
        "category": "Civil Registration",
        "fee": 25,
        "sla_days": 4,
        "required_documents": [
            {
                "id": "DOC-HOSPITAL",
                "name": "Hospital Birth Discharge Certificate / Form 1",
                "department_verifier": "Chief Medical Officer / Registrar Births",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Institutional delivery birth slip from hospital."
            },
            {
                "id": "DOC-PARENTS",
                "name": "Parents Aadhaar & Marriage Proof",
                "department_verifier": "UIDAI & Marriage Registry",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Aadhaar cards of mother and father."
            },
            {
                "id": "DOC-RESIDENCE",
                "name": "Utility Bill / Domicile Residence Proof",
                "department_verifier": "State Electricity Board / Civic Registry",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Electricity or water bill showing address."
            }
        ]
    },
    {
        "id": "SRV-EDU-06",
        "name": "Post-Matric Merit Scholarship Sanction",
        "department": "EDUCATION",
        "department_name": "Higher Education & Scholarship Wing",
        "category": "Higher Education & DBT",
        "fee": 0,
        "sla_days": 8,
        "required_documents": [
            {
                "id": "DOC-PAN",
                "name": "Student / Guardian PAN Card",
                "department_verifier": "Income Tax Department",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Permanent Account Number."
            },
            {
                "id": "DOC-MARKSHEET",
                "name": "Class 12 / Degree Marksheet (DigiLocker Verified)",
                "department_verifier": "National Academic Depository (NAD / DigiLocker)",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 5,
                "instructions": "Digital mark sheet with board validation."
            },
            {
                "id": "DOC-COLLEGE",
                "name": "College Admission Bonafide & Fee Receipt",
                "department_verifier": "University Registrar Portal",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 5,
                "instructions": "Official bonafide certificate with college seal."
            }
        ]
    }
]

DATABASE = {
    "departments": [
        {"id": "PENSION", "name": "Department of Pension & Pensioners' Welfare", "sla_days": 14, "officer_count": 8},
        {"id": "REVENUE", "name": "Department of Land & Revenue", "sla_days": 10, "officer_count": 12},
        {"id": "MUNICIPAL", "name": "Urban Local Bodies & Civic Affairs", "sla_days": 7, "officer_count": 15},
        {"id": "EDUCATION", "name": "Higher Education & Scholarship Wing", "sla_days": 12, "officer_count": 6}
    ],
    "officers": [
        {"id": "OFF-101", "name": "Rajesh Sharma", "department": "PENSION", "role": "Senior Sanctioning Officer", "active_load": 18, "status": "ACTIVE", "designation": "Deputy Secretary (Pension)"},
        {"id": "OFF-102", "name": "Priya Deshmukh", "department": "REVENUE", "role": "Tahsildar & Mutation Officer", "active_load": 24, "status": "HIGH_LOAD", "designation": "Executive Tahsildar"},
        {"id": "OFF-103", "name": "Anil Verma", "department": "MUNICIPAL", "role": "Chief Sanctioning Authority", "active_load": 9, "status": "ACTIVE", "designation": "Assistant Municipal Commissioner"},
        {"id": "OFF-104", "name": "Dr. Sandeep Kulkarni", "department": "EDUCATION", "role": "Director of Higher Education", "active_load": 7, "status": "ACTIVE", "designation": "Joint Director (Scholarships)"}
    ],
    "files": [
        {
            "id": "GOV-2026-8120",
            "applicant_name": "Sundareswaran Iyer",
            "applicant_phone": "9876543210",
            "department": "PENSION",
            "service_id": "SRV-PENSION-01",
            "service_name": "Senior Citizen Family Pension Sanction",
            "submission_date": "2026-09-08",
            "current_stage": "APPLICATION_SUBMITTED",
            "assigned_officer": "Rajesh Sharma",
            "assigned_officer_id": "OFF-101",
            "missing_documents_count": 0,
            "days_in_current_stage": 0,
            "complexity_score": 2,
            "is_grievance_escalated": False,
            "status": "VERIFIED_READY",
            "payment_status": "PAID_RAZORPAY",
            "payment_ref": "pay_rzp_81203914",
            "fee_paid": 50,
            "digilocker_verified": True,
            "uploaded_docs": [
                {"id": "DOC-AADHAAR", "name": "Applicant Aadhaar Card / e-KYC", "type": "AADHAAR", "filename": "applicant_aadhaar_card.pdf", "verifier": "Unique Identification Authority of India (UIDAI)", "verified": True, "token": "UIDAI-AADHAAR-8912"},
                {"id": "DOC-PPO", "name": "Pension Payment Order (PPO) / Succession Certificate", "type": "PPO", "filename": "ppo_succession_order.pdf", "verifier": "Central Pension Accounting Office (CPAO)", "verified": True, "token": "CPAO-PPO-7741"},
                {"id": "DOC-BANK", "name": "Bank Passbook / Cancelled Cheque (Mandate)", "type": "BANK", "filename": "bank_passbook_mandate.pdf", "verifier": "Public Sector Bank / NPCI Core Banking", "verified": True, "token": "NPCI-MANDATE-5521"},
                {"id": "DOC-PHOTO", "name": "Passport Size Photograph & Signature", "type": "PHOTO", "filename": "passport_photo_signature.pdf", "verifier": "DigiLocker Biometric Self-Attestation", "verified": True, "token": "DL-PHOTO-3319"}
            ],
            "delay_guidance": {
                "delay_reason": "Application freshly submitted with all verified documents. In normal queue.",
                "required_action": "None. Waiting for departmental officer scrutiny.",
                "next_step": "Document scrutiny & milestone advancement by officer desk."
            },
            "esign": None
        },
        {
            "id": "GOV-2026-7841",
            "applicant_name": "Kavitha Ramesh",
            "applicant_phone": "9876543210",
            "department": "REVENUE",
            "service_id": "SRV-REV-02",
            "service_name": "Agricultural Land Title Deed Mutation",
            "submission_date": "2026-09-07",
            "current_stage": "DOCUMENT_VERIFICATION",
            "assigned_officer": "Priya Deshmukh",
            "assigned_officer_id": "OFF-102",
            "missing_documents_count": 0,
            "days_in_current_stage": 1,
            "complexity_score": 3,
            "is_grievance_escalated": False,
            "status": "IN_PROGRESS",
            "payment_status": "PAID_RAZORPAY",
            "payment_ref": "pay_rzp_78410291",
            "fee_paid": 100,
            "digilocker_verified": True,
            "uploaded_docs": [
                {"id": "DOC-AADHAAR", "name": "Applicant Aadhaar Card", "type": "AADHAAR", "filename": "aadhaar_kavitha.pdf", "verifier": "UIDAI e-KYC", "verified": True, "token": "UIDAI-KYC-7841"},
                {"id": "DOC-DEED", "name": "Registered Sale Deed / Partition Deed Copy", "type": "DEED", "filename": "registered_sale_deed_2024.pdf", "verifier": "Sub-Registrar Office & Land Records", "verified": True, "token": "SRO-DEED-9912"},
                {"id": "DOC-ROR", "name": "Latest RoR / Patta / 7/12 Extract", "type": "ROR", "filename": "ror_patta_extract.pdf", "verifier": "Revenue e-Dharti Portal", "verified": True, "token": "EDHARTI-ROR-4412"},
                {"id": "DOC-TAX", "name": "Up-to-Date Land Revenue Tax Paid Challan", "type": "TAX", "filename": "land_tax_challan.pdf", "verifier": "State Treasury / e-Challan", "verified": True, "token": "TREASURY-TAX-1029"}
            ],
            "delay_guidance": {
                "delay_reason": "Under active Tahsildar scrutiny.",
                "required_action": "None. Keep tracking online.",
                "next_step": "Field Inspector verification."
            },
            "esign": None
        },
        {
            "id": "GOV-2026-9210",
            "applicant_name": "Gurpreet Singh",
            "applicant_phone": "9876543210",
            "department": "MUNICIPAL",
            "service_id": "SRV-MUN-03",
            "service_name": "Commercial Water Connection NOC",
            "submission_date": "2026-09-01",
            "current_stage": "DISPATCH_DIGILOCKER",
            "assigned_officer": "Anil Verma",
            "assigned_officer_id": "OFF-103",
            "missing_documents_count": 0,
            "days_in_current_stage": 1,
            "complexity_score": 2,
            "is_grievance_escalated": False,
            "status": "COMPLETED",
            "payment_status": "PAID_RAZORPAY",
            "payment_ref": "pay_rzp_92104829",
            "fee_paid": 200,
            "digilocker_verified": True,
            "uploaded_docs": [
                {"id": "DOC-AADHAAR", "name": "Proprietor / Authorized Signatory Aadhaar", "type": "AADHAAR", "filename": "pan_gurpreet_singh.pdf", "verifier": "UIDAI", "verified": True, "token": "UIDAI-AADHAAR-9210"},
                {"id": "DOC-PROP", "name": "Municipal Property Tax Assessment / Holding Receipt", "type": "PROPERTY", "filename": "property_tax_ward14.pdf", "verifier": "ULB Property Tax Wing", "verified": True, "token": "ULB-PROP-9812"},
                {"id": "DOC-BLDG", "name": "Approved Building Sanction Plan (Site Drawing)", "type": "PLAN", "filename": "plumbing_layout_v2.pdf", "verifier": "Town & Country Planning Directorate", "verified": True, "token": "TPD-SITE-OK-881"},
                {"id": "DOC-TRADE", "name": "Trade License / Fire NOC", "type": "FIRE", "filename": "fire_noc_2026.pdf", "verifier": "Directorate of Fire & Emergency Services", "verified": True, "token": "FES-CLEAR-441"}
            ],
            "delay_guidance": {
                "delay_reason": "Service completed & officially E-Signed by Municipal Sanctioning Authority.",
                "required_action": "Download your official certificate from the citizen portal or DigiLocker.",
                "next_step": "Service Delivered."
            },
            "esign": {
                "signed_by": "Anil Verma",
                "designation": "Assistant Municipal Commissioner",
                "timestamp": "09 Sep 2026, 14:30:00 IST",
                "cert_hash": "4f88e9102c1109a823",
                "status": "OFFICIALLY_ISSUED"
            }
        },
        {
            "id": "GOV-2026-6312",
            "applicant_name": "Suresh Natarajan",
            "applicant_phone": "9876543210",
            "department": "MUNICIPAL",
            "service_id": "SRV-MUN-03",
            "service_name": "Commercial Water Connection NOC",
            "submission_date": "2026-09-09",
            "current_stage": "APPLICATION_SUBMITTED",
            "assigned_officer": "Anil Verma",
            "assigned_officer_id": "OFF-103",
            "missing_documents_count": 0,
            "days_in_current_stage": 0,
            "complexity_score": 2,
            "is_grievance_escalated": False,
            "status": "VERIFIED_READY",
            "payment_status": "PAID_RAZORPAY",
            "payment_ref": "pay_rzp_63120194",
            "fee_paid": 200,
            "digilocker_verified": True,
            "uploaded_docs": [
                {"id": "DOC-AADHAAR", "name": "Proprietor / Authorized Signatory Aadhaar", "type": "AADHAAR", "filename": "aadhaar_suresh.pdf", "verifier": "UIDAI", "verified": True, "token": "UIDAI-AADHAAR-6312"},
                {"id": "DOC-PROP", "name": "Municipal Property Tax Assessment / Holding Receipt", "type": "PROPERTY", "filename": "prop_tax_ward7.pdf", "verifier": "ULB Property Tax Wing", "verified": True, "token": "ULB-PROP-6312"},
                {"id": "DOC-BLDG", "name": "Approved Building Sanction Plan (Site Drawing)", "type": "PLAN", "filename": "site_plumbing_layout.pdf", "verifier": "Town Planning Directorate", "verified": True, "token": "TPD-SITE-OK-631"},
                {"id": "DOC-TRADE", "name": "Trade License / Fire NOC", "type": "FIRE", "filename": "trade_lic_2026.pdf", "verifier": "Civic Health Dept", "verified": True, "token": "CHD-LIC-631"}
            ],
            "delay_guidance": {
                "delay_reason": "Application freshly submitted with all verified documents. In normal queue.",
                "required_action": "None. Waiting for departmental officer scrutiny.",
                "next_step": "Document scrutiny & milestone advancement by officer desk."
            },
            "esign": None
        },
        {
            "id": "GOV-2026-5104",
            "applicant_name": "Aarav Sharma",
            "applicant_phone": "9876543210",
            "department": "EDUCATION",
            "service_id": "SRV-EDU-06",
            "service_name": "Post-Matric Merit Scholarship Sanction",
            "submission_date": "2026-09-08",
            "current_stage": "OFFICER_REVIEW",
            "assigned_officer": "Dr. Sandeep Kulkarni",
            "assigned_officer_id": "OFF-104",
            "missing_documents_count": 0,
            "days_in_current_stage": 2,
            "complexity_score": 1,
            "is_grievance_escalated": False,
            "status": "IN_PROGRESS",
            "payment_status": "PAID_RAZORPAY",
            "payment_ref": "pay_rzp_51049210",
            "fee_paid": 0,
            "digilocker_verified": True,
            "uploaded_docs": [
                {"id": "DOC-PAN", "name": "Student / Guardian PAN Card", "type": "PAN", "filename": "pan_aarav.pdf", "verifier": "Income Tax Department", "verified": True, "token": "ITD-PAN-5104"},
                {"id": "DOC-MARKSHEET", "name": "Class 12 / Degree Marksheet (DigiLocker Verified)", "type": "MARKSHEET", "filename": "class12_marksheet_digilocker.pdf", "verifier": "National Academic Depository (NAD / DigiLocker)", "verified": True, "token": "NAD-MARK-8831"},
                {"id": "DOC-COLLEGE", "name": "College Admission Bonafide & Fee Receipt", "type": "COLLEGE", "filename": "college_bonafide_2026.pdf", "verifier": "University Registrar Portal", "verified": True, "token": "UNIV-BONAFIDE-7712"}
            ],
            "delay_guidance": {
                "delay_reason": "Academic marks and bonafide under verification.",
                "required_action": "None. Verification in final stages.",
                "next_step": "Final sanction & DBT release."
            },
            "esign": None
        }
    ],
        "grievances": [
        {
            "id": "CPGRAMS-2026-9812",
            "citizen_name": "Sundareswaran Iyer",
            "citizen_phone": "9876543210",
            "file_id": "GOV-2026-8120",
            "service_name": "Senior Citizen Family Pension Sanction",
            "department": "PENSION",
            "category": "Inordinate Processing Delay / SLA Exceeded",
            "priority": "URGENT",
            "description": "Pension payment order succession verification has been pending for over 5 days without officer review notes.",
            "status": "ESCALATED_TO_DEPT_HEAD",
            "timestamp": "08 Sep 2026, 18:30:00 IST",
            "officer_action": "Department Head issued priority notice to Senior Sanctioning Officer."
        }
    ],
"issued_certificates": [],
    "audit_logs": [],
    "webhook_logs": []
}

def cross_verify_with_department(doc_type: str, doc_name: str, applicant_name: str):
    if "PAN" in doc_type.upper() or "PAN" in doc_name.upper():
        return {
            "department": "Income Tax Department (CBDT / NSDL)",
            "status": "AUTHENTIC_VERIFIED",
            "message": f"PAN record matched with Income Tax Database for {applicant_name}. Status: ACTIVE.",
            "verification_token": f"ITD-PAN-{hashlib.md5(applicant_name.encode()).hexdigest()[:8].upper()}"
        }
    elif "AADHAAR" in doc_type.upper() or "AADHAAR" in doc_name.upper():
        return {
            "department": "Unique Identification Authority of India (UIDAI)",
            "status": "AUTHENTIC_VERIFIED",
            "message": f"UIDAI e-KYC record validated via DigiLocker OTP bridge for {applicant_name}.",
            "verification_token": f"UIDAI-KYC-{hashlib.md5((applicant_name+'uidai').encode()).hexdigest()[:8].upper()}"
        }
    else:
        return {
            "department": "State Government Directorate / Municipal Registry",
            "status": "AUTHENTIC_VERIFIED",
            "message": f"Endorsement authenticity confirmed in official registry for {doc_name}.",
            "verification_token": f"SGR-DOC-{hashlib.md5(doc_name.encode()).hexdigest()[:8].upper()}"
        }

def enrich_file_with_prediction(file_obj):
    officer = next((o for o in DATABASE["officers"] if o["id"] == file_obj.get("assigned_officer_id")), None)
    backlog = officer["active_load"] if officer else 12

    payload = {
        "department": file_obj["department"],
        "current_stage": file_obj["current_stage"],
        "missing_documents_count": file_obj.get("missing_documents_count", 0),
        "assigned_officer_backlog": backlog,
        "days_in_current_stage": file_obj.get("days_in_current_stage", 1),
        "complexity_score": file_obj.get("complexity_score", 2),
        "is_grievance_escalated": file_obj.get("is_grievance_escalated", False)
    }

    prediction = predict_delay_and_eta(payload)
    enriched = {**file_obj, "prediction": prediction}
    return enriched

def trigger_webhook_event(event_type: str, file_data: dict, details: str):
    secret_key = b"civiora_sih_2026_gov_secret"
    payload_str = json.dumps({"event": event_type, "file_id": file_data.get("id"), "timestamp": datetime.now().isoformat()})
    signature = hmac.new(secret_key, payload_str.encode('utf-8'), hashlib.sha256).hexdigest()

    targets = ["DigiLocker Secure Store API", "UMANG Push Notification Gateway", "SMS / WhatsApp Gov-Alert"]

    for target in targets:
        webhook_entry = {
            "id": f"WH-{int(time.time()*1000)%1000000}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": event_type,
            "target": target,
            "file_id": file_data.get("id"),
            "signature": f"sha256={signature[:16]}...",
            "status": "DELIVERED (HTTP 200 OK)",
            "retry_count": 0,
            "details": details
        }
        DATABASE["webhook_logs"].insert(0, webhook_entry)

def log_audit(action: str, performed_by: str, file_id: str, notes: str):
    audit_entry = {
        "id": f"AUD-{len(DATABASE['audit_logs']) + 1001}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "performed_by": performed_by,
        "file_id": file_id,
        "notes": notes
    }
    DATABASE["audit_logs"].insert(0, audit_entry)
