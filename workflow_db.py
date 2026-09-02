"""
Civiora SIH Webhook, Workflow & Persistence Engine
Handles mock database, audit logs, webhook triggers (DigiLocker, SMS/Email), RBAC,
Service Catalogs, and Smart Document Verification logic per specification.
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
        "category": "Welfare & Pension",
        "fee": 50,
        "sla_days": 14,
        "description": "Application for pension disbursement to eligible senior citizens or legal heirs.",
        "required_documents": [
            {
                "id": "DOC-AADHAAR",
                "name": "Aadhaar Card",
                "mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "max_size_mb": 5,
                "instructions": "Upload a clear copy. Ensure full 12 digits and address are readable.",
                "validity": "Current / Active UIDAI record"
            },
            {
                "id": "DOC-BANK",
                "name": "Bank Passbook / Cancelled Cheque",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Must show Account Number, IFSC code, and Account Holder Name clearly.",
                "validity": "Active Nationalized Bank Account"
            },
            {
                "id": "DOC-AGE",
                "name": "Age Proof / Birth Certificate",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Proof that applicant age is 60+ years.",
                "validity": "Issued by Municipal / Registrar"
            }
        ]
    },
    {
        "id": "SRV-REV-02",
        "name": "Agricultural Land Title Deed Mutation",
        "department": "REVENUE",
        "department_name": "Department of Land & Revenue",
        "category": "Land & Revenue",
        "fee": 150,
        "sla_days": 10,
        "description": "Transfer or mutation of land title in revenue records after sale or succession.",
        "required_documents": [
            {
                "id": "DOC-AADHAAR",
                "name": "Aadhaar Card of Buyer / Successor",
                "mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "max_size_mb": 5,
                "instructions": "UIDAI identity proof with matching signature.",
                "validity": "Valid"
            },
            {
                "id": "DOC-DEED",
                "name": "Registered Sale Deed / Title Document",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 10,
                "instructions": "Must include Sub-Registrar seal, book number, and survey bounds.",
                "validity": "Sub-Registrar Endorsed"
            },
            {
                "id": "DOC-TAX",
                "name": "Latest Land Tax Paid Receipt",
                "mandatory": False,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Proof of zero pending revenue tax dues.",
                "validity": "Current Financial Year"
            }
        ]
    },
    {
        "id": "SRV-MUN-03",
        "name": "Commercial Water Connection NOC",
        "department": "MUNICIPAL",
        "department_name": "Urban Local Bodies & Civic Affairs",
        "category": "Civic Utilities & Permits",
        "fee": 200,
        "sla_days": 7,
        "description": "No-Objection Certificate and pipeline meter sanction for commercial premises.",
        "required_documents": [
            {
                "id": "DOC-AADHAAR",
                "name": "Aadhaar Card of Business Owner",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Identity proof of proprietor or authorized signatory.",
                "validity": "Valid"
            },
            {
                "id": "DOC-PROPERTY",
                "name": "Property Tax Receipt / Ownership Proof",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Showing municipal ward and assessment number.",
                "validity": "Current year"
            },
            {
                "id": "DOC-PLAN",
                "name": "Approved Building Site Plan",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 10,
                "instructions": "Architect approved plumbing layout map.",
                "validity": "Town Planning Approved"
            }
        ]
    },
    {
        "id": "SRV-EDU-04",
        "name": "National Post-Graduate Merit Scholarship",
        "department": "EDUCATION",
        "department_name": "Higher Education & Scholarship Wing",
        "category": "Education & Schemes",
        "fee": 0,
        "sla_days": 12,
        "description": "Direct Benefit Transfer (DBT) scholarship disbursement for PG students.",
        "required_documents": [
            {
                "id": "DOC-AADHAAR",
                "name": "Aadhaar Card",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Must be seeded with bank account for DBT payment.",
                "validity": "Valid"
            },
            {
                "id": "DOC-INCOME",
                "name": "Annual Family Income Certificate",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Issued by Tahsildar / Competent Revenue Authority (< Rs. 2.5 Lakhs).",
                "validity": "Valid for current FY"
            },
            {
                "id": "DOC-MARKS",
                "name": "Undergraduate Degree Marksheet",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 5,
                "instructions": "Showing minimum 60% aggregate score.",
                "validity": "University Verified"
            }
        ]
    }
]

DATABASE = {
    "departments": [
        {"id": "PENSION", "name": "Department of Pension & Pensioners' Welfare", "sla_days": 14, "officer_count": 8},
        {"id": "REVENUE", "name": "Department of Land & Revenue", "sla_days": 10, "officer_count": 12},
        {"id": "MUNICIPAL", "name": "Urban Local Bodies & Civic Affairs", "sla_days": 7, "officer_count": 15},
        {"id": "EDUCATION", "name": "Higher Education & Scholarship Wing", "sla_days": 12, "officer_count": 6},
        {"id": "HEALTH", "name": "Public Health & Medical Services", "sla_days": 5, "officer_count": 10}
    ],
    "officers": [
        {"id": "OFF-101", "name": "Rajesh Sharma", "department": "PENSION", "role": "Senior Review Officer", "active_load": 18, "status": "ACTIVE"},
        {"id": "OFF-102", "name": "Priya Deshmukh", "department": "REVENUE", "role": "Tahsildar Verification Officer", "active_load": 24, "status": "HIGH_LOAD"},
        {"id": "OFF-103", "name": "Anil Verma", "department": "MUNICIPAL", "role": "Sanctioning Authority", "active_load": 9, "status": "ACTIVE"},
        {"id": "OFF-104", "name": "Sunita Nair", "department": "EDUCATION", "role": "Scholarship Desk Head", "active_load": 14, "status": "ACTIVE"}
    ],
    "files": [
        {
            "id": "GOV-2026-8819",
            "applicant_name": "Ramesh Chandra",
            "applicant_phone": "9876543210",
            "department": "PENSION",
            "service_id": "SRV-PENSION-01",
            "service_name": "Senior Citizen Family Pension Sanction",
            "submission_date": "2026-08-25",
            "current_stage": "INTER_DEPT_NOC",
            "assigned_officer": "Rajesh Sharma",
            "assigned_officer_id": "OFF-101",
            "missing_documents_count": 1,
            "days_in_current_stage": 6,
            "complexity_score": 4,
            "is_grievance_escalated": True,
            "status": "ACTION_REQUIRED",
            "payment_status": "PAID",
            "fee_paid": 50,
            "digilocker_verified": True,
            "delay_guidance": {
                "delay_reason": "Inter-department NOC pending due to verification of nomination certificate.",
                "required_action": "No citizen action required currently. Escalated to Dept Desk.",
                "next_step": "Awaiting approval from Pension Sanctioning Authority."
            }
        },
        {
            "id": "GOV-2026-9042",
            "applicant_name": "Ananya Mukherjee",
            "applicant_phone": "9845012345",
            "department": "REVENUE",
            "service_id": "SRV-REV-02",
            "service_name": "Agricultural Land Title Deed Mutation",
            "submission_date": "2026-08-28",
            "current_stage": "DOCUMENT_VERIFICATION",
            "assigned_officer": "Priya Deshmukh",
            "assigned_officer_id": "OFF-102",
            "missing_documents_count": 1,
            "days_in_current_stage": 4,
            "complexity_score": 3,
            "is_grievance_escalated": False,
            "status": "ACTION_REQUIRED",
            "payment_status": "PAID",
            "fee_paid": 150,
            "digilocker_verified": False,
            "delay_guidance": {
                "delay_reason": "Uploaded Title Deed page 2 seal is blurred and unreadable.",
                "required_action": "Please re-upload a clear copy of Registered Sale Deed with visible Sub-Registrar seal.",
                "next_step": "Re-upload document to resume verification."
            }
        },
        {
            "id": "GOV-2026-9210",
            "applicant_name": "Gurpreet Singh",
            "applicant_phone": "9123456789",
            "department": "MUNICIPAL",
            "service_id": "SRV-MUN-03",
            "service_name": "Commercial Water Connection NOC",
            "submission_date": "2026-09-01",
            "current_stage": "OFFICER_REVIEW",
            "assigned_officer": "Anil Verma",
            "assigned_officer_id": "OFF-103",
            "missing_documents_count": 0,
            "days_in_current_stage": 1,
            "complexity_score": 2,
            "is_grievance_escalated": False,
            "status": "ON_TRACK",
            "payment_status": "PAID",
            "fee_paid": 200,
            "digilocker_verified": True,
            "delay_guidance": {
                "delay_reason": "All documents verified. In normal officer review queue.",
                "required_action": "None. Application is progressing within standard SLA.",
                "next_step": "Final sanction order dispatch to DigiLocker."
            }
        }
    ],
    "audit_logs": [],
    "webhook_logs": []
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
