"""
Civiora SIH Webhook, Workflow, Payment & Departmental Cross-Verification Engine
Handles services catalog with distinct document requirements per service,
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
        "category": "Welfare & Pension",
        "fee": 50,
        "sla_days": 14,
        "required_documents": [
            {
                "id": "DOC-PAN",
                "name": "PAN Card (Identity & Tax Record)",
                "department_verifier": "Income Tax Department (CBDT / NSDL)",
                "mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "max_size_mb": 5,
                "instructions": "Clear copy showing 10-character alphanumeric PAN and photograph."
            },
            {
                "id": "DOC-AADHAAR",
                "name": "Aadhaar Card (UIDAI Age & Address Proof)",
                "department_verifier": "Unique Identification Authority of India (UIDAI)",
                "mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "max_size_mb": 5,
                "instructions": "UIDAI identity proof with verifiable QR code showing DOB."
            },
            {
                "id": "DOC-BANK",
                "name": "Bank Passbook / Cancelled Cheque (DBT Linkage)",
                "department_verifier": "Public Financial Management System (PFMS)",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Must show Account Number, IFSC code, and Account Holder Name."
            },
            {
                "id": "DOC-PPO",
                "name": "Pension Payment Order (PPO) Copy / Death Certificate",
                "department_verifier": "Central Pension Accounting Office (CPAO)",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 10,
                "instructions": "Prior PPO document or legal heir succession certificate."
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
        "required_documents": [
            {
                "id": "DOC-PAN",
                "name": "Buyer / Successor PAN Card",
                "department_verifier": "Income Tax Department",
                "mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "max_size_mb": 5,
                "instructions": "PAN card of the property purchaser or legal successor."
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
                "name": "Land Revenue Tax Paid Receipt (Khata Extract)",
                "department_verifier": "Gram Panchayat / Tahsildar Land Records",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Latest land tax receipt and village 7/12 extract."
            },
            {
                "id": "DOC-ENCUMB",
                "name": "Non-Encumbrance Certificate (EC)",
                "department_verifier": "Inspector General of Registration (IGR)",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 5,
                "instructions": "15-year non-encumbrance certificate issued by Sub-Registrar."
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
                "name": "Approved Site Plumbing & Drainage Plan",
                "department_verifier": "Town Planning & Engineering Directorate",
                "mandatory": True,
                "accepted_formats": "PDF",
                "max_size_mb": 10,
                "instructions": "Architect approved plumbing layout map."
            },
            {
                "id": "DOC-FIRE",
                "name": "Fire Safety NOC / Trade License",
                "department_verifier": "Fire & Emergency Services / Civic Health Dept",
                "mandatory": True,
                "accepted_formats": "PDF, JPG",
                "max_size_mb": 5,
                "instructions": "Current valid fire clearance or civic trade license."
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
                {"name": "Business Proprietor PAN Card", "type": "PAN", "filename": "pan_gurpreet_singh.pdf", "verifier": "Income Tax Department (CBDT)", "verified": True, "token": "ITD-PAN-VERIFIED-9821"},
                {"name": "Property Tax Assessment Receipt", "type": "PROPERTY", "filename": "property_tax_ward14.pdf", "verifier": "Urban Local Body Property Registry", "verified": True, "token": "ULB-PROP-9812"},
                {"name": "Approved Site Plumbing & Drainage Plan", "type": "PLAN", "filename": "plumbing_layout_v2.pdf", "verifier": "Town Planning Directorate", "verified": True, "token": "TPD-SITE-OK-881"},
                {"name": "Fire Safety NOC / Trade License", "type": "FIRE", "filename": "fire_noc_2026.pdf", "verifier": "Fire & Emergency Services", "verified": True, "token": "FES-CLEAR-441"}
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
                {"name": "Business Proprietor PAN Card", "type": "PAN", "filename": "pan_suresh_natarajan.pdf", "verifier": "Income Tax Department (CBDT)", "verified": True, "token": "ITD-PAN-VERIFIED-6312"},
                {"name": "Property Tax Assessment Receipt", "type": "PROPERTY", "filename": "prop_tax_ward7.pdf", "verifier": "Urban Local Body Property Registry", "verified": True, "token": "ULB-PROP-6312"},
                {"name": "Approved Site Plumbing & Drainage Plan", "type": "PLAN", "filename": "site_plumbing_layout.pdf", "verifier": "Town Planning Directorate", "verified": True, "token": "TPD-SITE-OK-631"},
                {"name": "Fire Safety NOC / Trade License", "type": "FIRE", "filename": "trade_lic_2026.pdf", "verifier": "Civic Health Dept", "verified": True, "token": "CHD-LIC-631"}
            ],
            "delay_guidance": {
                "delay_reason": "Application freshly submitted with all verified documents. In normal queue.",
                "required_action": "None. Waiting for departmental officer scrutiny.",
                "next_step": "Document scrutiny & milestone advancement by officer desk."
            },
            "esign": None
        }
    ],
    "issued_certificates": [],
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
