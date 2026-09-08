"""
Civiora SIH Webhook, Workflow, Payment & Departmental Cross-Verification Engine
Handles mock database, audit logs, Razorpay payment tokens, E-Sign records,
and Departmental verification APIs (Income Tax PAN, UIDAI Aadhaar, Land Registry).
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
        "instructions": [
            "Applicant must be 60 years or older (or designated legal heir).",
            "Keep your PAN Card and Aadhaar Card ready for real-time Income Tax & UIDAI database cross-verification.",
            "Ensure bank account is seeded with Aadhaar for Direct Benefit Transfer (DBT).",
            "Payment of ₹50.00 Government sanction fee can be made via Razorpay (UPI/QR/Card)."
        ],
        "required_documents": [
            {
                "id": "DOC-PAN",
                "name": "PAN Card",
                "department_verifier": "Income Tax Department (ITD NSDL / UTIITSL)",
                "mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "max_size_mb": 5,
                "instructions": "Clear copy showing 10-character alphanumeric PAN and photograph."
            },
            {
                "id": "DOC-AADHAAR",
                "name": "Aadhaar Card",
                "department_verifier": "Unique Identification Authority of India (UIDAI)",
                "mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "max_size_mb": 5,
                "instructions": "UIDAI identity proof with verifiable QR code."
            },
            {
                "id": "DOC-BANK",
                "name": "Bank Passbook / Cancelled Cheque",
                "department_verifier": "Public Financial Management System (PFMS)",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Must show Account Number, IFSC code, and Account Holder Name."
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
        "instructions": [
            "Applicant must possess a registered sale deed or succession decree endorsed by the Sub-Registrar.",
            "PAN Card will be cross-checked with Income Tax Department records for buyer identity.",
            "Property survey numbers will be verified against the State Revenue Land Records database.",
            "Statutory fee of ₹150.00 is payable via Razorpay."
        ],
        "required_documents": [
            {
                "id": "DOC-PAN",
                "name": "Buyer / Successor PAN Card",
                "department_verifier": "Income Tax Department",
                "mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "max_size_mb": 5,
                "instructions": "PAN card of the property purchaser or heir."
            },
            {
                "id": "DOC-DEED",
                "name": "Registered Sale Deed / Title Document",
                "department_verifier": "State Registration & Stamps Department",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 10,
                "instructions": "Sub-Registrar registered document showing book number and survey bounds."
            },
            {
                "id": "DOC-TAX",
                "name": "Land Revenue Tax Paid Receipt",
                "department_verifier": "Gram Panchayat / Municipal Revenue Registry",
                "mandatory": False,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Latest land tax receipt for current fiscal year."
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
        "instructions": [
            "Commercial establishments must have an approved building site plan.",
            "PAN Card of the proprietor will be verified with the Income Tax Department.",
            "Property assessment will be cross-verified with the Municipal Ward Registry.",
            "Connection inspection fee of ₹200.00 is processed securely via Razorpay."
        ],
        "required_documents": [
            {
                "id": "DOC-PAN",
                "name": "Business Proprietor PAN Card",
                "department_verifier": "Income Tax Department (CBDT)",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "PAN of applicant / enterprise authorized signatory."
            },
            {
                "id": "DOC-PROPERTY",
                "name": "Property Tax Assessment Receipt",
                "department_verifier": "Urban Local Body Property Tax Registry",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Showing municipal ward and assessment number."
            },
            {
                "id": "DOC-PLAN",
                "name": "Approved Site Plumbing Plan",
                "department_verifier": "Town Planning & Engineering Directorate",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 10,
                "instructions": "Architect approved plumbing layout map."
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
        {"id": "OFF-103", "name": "Anil Verma", "department": "MUNICIPAL", "role": "Chief Sanctioning Authority", "active_load": 9, "status": "ACTIVE", "designation": "Assistant Municipal Commissioner"}
    ],
    "files": [
        {
            "id": "GOV-2026-9210",
            "applicant_name": "Gurpreet Singh",
            "applicant_phone": "9876543210",
            "department": "MUNICIPAL",
            "service_id": "SRV-MUN-03",
            "service_name": "Commercial Water Connection NOC",
            "submission_date": "2026-09-01",
            "current_stage": "FINAL_APPROVAL",
            "assigned_officer": "Anil Verma",
            "assigned_officer_id": "OFF-103",
            "missing_documents_count": 0,
            "days_in_current_stage": 1,
            "complexity_score": 2,
            "is_grievance_escalated": False,
            "status": "PENDING_ESIGN",
            "payment_status": "PAID_RAZORPAY",
            "payment_ref": "pay_rzp_92104829",
            "fee_paid": 200,
            "digilocker_verified": True,
            "uploaded_docs": [
                {"name": "Proprietor PAN Card", "type": "PAN", "filename": "pan_gurpreet_singh.pdf", "verifier": "Income Tax Department", "verified": True, "token": "ITD-PAN-VERIFIED-9821"},
                {"name": "Property Tax Receipt", "type": "PROPERTY", "filename": "property_tax_ward14.pdf", "verifier": "Municipal Registry", "verified": True, "token": "ULB-PROP-9812"},
                {"name": "Approved Plumbing Site Plan", "type": "PLAN", "filename": "plumbing_layout_v2.pdf", "verifier": "Town Planning Dept", "verified": True, "token": "TPD-SITE-OK"}
            ],
            "delay_guidance": {
                "delay_reason": "All departmental cross-verifications completed. Waiting for Final Officer Digital E-Signature.",
                "required_action": "None. E-Signed certificate will be dispatched automatically.",
                "next_step": "Final Officer E-Sign & Certificate Dispatch to Citizen Portal."
            },
            "esign": None
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
            "missing_documents_count": 0,
            "days_in_current_stage": 2,
            "complexity_score": 3,
            "is_grievance_escalated": False,
            "status": "IN_PROGRESS",
            "payment_status": "PAID_RAZORPAY",
            "payment_ref": "pay_rzp_88410294",
            "fee_paid": 150,
            "digilocker_verified": True,
            "uploaded_docs": [
                {"name": "Buyer PAN Card", "type": "PAN", "filename": "pan_ananya_mukherjee.pdf", "verifier": "Income Tax Department", "verified": True, "token": "ITD-PAN-VERIFIED-4412"},
                {"name": "Registered Sale Deed", "type": "DEED", "filename": "title_deed_scan.pdf", "verifier": "State Registration & Stamps", "verified": True, "token": "REG-STAMP-5521"}
            ],
            "delay_guidance": {
                "delay_reason": "Cross-verification with State Revenue Land Records database in progress.",
                "required_action": "No action required.",
                "next_step": "Officer Review milestone advancement."
            },
            "esign": None
        }
    ],
    "issued_certificates": [],
    "audit_logs": [],
    "webhook_logs": []
}

def cross_verify_with_department(doc_type: str, doc_name: str, applicant_name: str):
    """
    Simulates real-time API call to Indian Government Departments
    e.g. Income Tax PAN Database, UIDAI Aadhaar, State Land Revenue Records.
    """
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
