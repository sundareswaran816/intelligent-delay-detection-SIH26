"""
Civiora SIH Web Application Server (FastAPI + Jinja2 + Webhooks + AI Engine + Razorpay + Digital E-Sign)
"""
import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
import random
import hashlib

from ai_engine import predict_delay_and_eta, STAGES, DEPARTMENT_BENCHMARKS
from workflow_db import (
    DATABASE,
    SERVICES_CATALOG,
    enrich_file_with_prediction,
    trigger_webhook_event,
    log_audit,
    cross_verify_with_department
)

app = FastAPI(title="Civiora Government File Verification & Workflow Portal - SIH 2026")

templates = Jinja2Templates(directory="templates")

# Initial Webhook
if not DATABASE["webhook_logs"]:
    trigger_webhook_event("SYSTEM_INITIALIZED", {"id": "SYS-BOOT"}, "Civiora Verification Engine & Webhooks Ready.")

# ================= STEP 1: CHOOSE ROLE ON HOME =================
@app.get("/", response_class=HTMLResponse)
async def home_choose_role(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="choose_role.html",
        context={"user_role": None}
    )

# ================= CITIZEN AUTHENTICATION (Mobile -> OTP) =================
@app.get("/login/citizen", response_class=HTMLResponse)
async def login_citizen_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login_citizen.html",
        context={"user_role": None, "otp_sent": False, "mobile_number": ""}
    )

@app.post("/auth/citizen/send-otp")
async def citizen_send_otp(request: Request, mobile_number: str = Form(...)):
    return templates.TemplateResponse(
        request=request,
        name="login_citizen.html",
        context={"user_role": None, "otp_sent": True, "mobile_number": mobile_number.strip(), "demo_otp": "123456"}
    )

@app.post("/auth/citizen/verify-otp")
async def citizen_verify_otp(request: Request, mobile_number: str = Form(...), otp: str = Form(...)):
    if otp.strip() in ["123456", "999999", "888888"] or len(otp.strip()) == 6:
        log_audit("CITIZEN_LOGIN", f"Citizen Phone: {mobile_number}", "AUTH-SESSION", "OTP Authentication verified successfully.")
        return RedirectResponse(url="/citizen", status_code=303)
    else:
        return templates.TemplateResponse(
            request=request,
            name="login_citizen.html",
            context={"user_role": None, "otp_sent": True, "mobile_number": mobile_number, "demo_otp": "123456", "error": "Invalid OTP."}
        )

# ================= OFFICER AUTHENTICATION =================
@app.get("/login/officer", response_class=HTMLResponse)
async def login_officer_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login_officer.html",
        context={"user_role": None, "departments": DATABASE["departments"]}
    )

@app.post("/auth/officer/verify")
async def officer_verify_credentials(request: Request, department: str = Form(...), officer_login_id: str = Form(...), password: str = Form(...)):
    clean_id = officer_login_id.strip().upper()
    matched_officer = next((o for o in DATABASE["officers"] if o["id"].upper() == clean_id), None)
    if not matched_officer:
        matched_officer = next((o for o in DATABASE["officers"] if o["department"].upper() == department.upper()), None)

    if matched_officer and (password.strip() in ["gov@2026", "admin"]):
        target_id = matched_officer["id"]
        log_audit("OFFICER_LOGIN", f"Officer ID: {target_id}", "AUTH-SESSION", f"Credentials authenticated for {department} department.")
        return RedirectResponse(url=f"/officer?officer_id={target_id}", status_code=303)
    else:
        return templates.TemplateResponse(
            request=request,
            name="login_officer.html",
            context={"user_role": None, "departments": DATABASE["departments"], "error": "Invalid Officer Credentials or PIN. (Demo: gov@2026)"}
        )

@app.get("/logout")
async def logout():
    return RedirectResponse(url="/", status_code=303)

# ================= CITIZEN PORTAL (Tracking + Certificate Download Hub) =================
@app.get("/citizen", response_class=HTMLResponse)
async def citizen_portal(request: Request, search_id: str = None):
    files = [enrich_file_with_prediction(f) for f in DATABASE["files"]]
    completed_files = [f for f in files if f.get("current_stage") == "DISPATCH_DIGILOCKER" or f.get("status") == "COMPLETED"]
    
    selected_file = None
    if search_id:
        selected_file = next((f for f in files if f["id"].lower() == search_id.strip().lower()), None)
    elif files:
        selected_file = files[0]
    
    return templates.TemplateResponse(
        request=request,
        name="citizen.html",
        context={
            "user_role": "citizen",
            "files": files,
            "completed_files": completed_files,
            "selected_file": selected_file,
            "search_id": search_id or (selected_file["id"] if selected_file else ""),
            "departments": DATABASE["departments"],
            "stages": STAGES
        }
    )

# ================= CITIZEN WIZARD (Instructions -> Requirements -> Upload -> Razorpay -> Dept Cross Check) =================
@app.get("/citizen/wizard", response_class=HTMLResponse)
async def citizen_wizard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="citizen_wizard.html",
        context={
            "user_role": "citizen",
            "services": SERVICES_CATALOG,
            "departments": DATABASE["departments"]
        }
    )

@app.post("/citizen/wizard/complete")
async def citizen_wizard_complete(
    request: Request,
    selected_service_id: str = Form(...),
    applicant_name: str = Form(...),
    applicant_phone: str = Form(...),
    payment_ref: str = Form("pay_rzp_9812401")
):
    service = next((s for s in SERVICES_CATALOG if s["id"] == selected_service_id), SERVICES_CATALOG[0])
    new_id = f"GOV-2026-{random.randint(1000, 9999)}"
    
    dept_officers = [o for o in DATABASE["officers"] if o["department"] == service["department"]]
    assigned_officer = random.choice(dept_officers) if dept_officers else DATABASE["officers"][0]
    
    new_file = {
        "id": new_id,
        "applicant_name": applicant_name,
        "applicant_phone": applicant_phone,
        "department": service["department"],
        "service_id": service["id"],
        "service_name": service["name"],
        "submission_date": datetime.now().strftime("%Y-%m-%d"),
        "current_stage": "APPLICATION_SUBMITTED",
        "assigned_officer": assigned_officer["name"],
        "assigned_officer_id": assigned_officer["id"],
        "missing_documents_count": 0,
        "days_in_current_stage": 0,
        "complexity_score": 2,
        "is_grievance_escalated": False,
        "status": "VERIFIED_READY",
        "payment_status": "PAID_RAZORPAY",
        "payment_ref": payment_ref,
        "fee_paid": service["fee"],
        "digilocker_verified": True,
        "uploaded_docs": [
            {"name": "Applicant PAN Card", "type": "PAN", "filename": "pan_applicant.pdf", "verifier": "Income Tax Department", "verified": True, "token": f"ITD-PAN-VERIFIED-{random.randint(1000,9999)}"},
            {"name": "Supporting Proof / Scheme Document", "type": "DEED", "filename": "supporting_doc.pdf", "verifier": "State Authority Registry", "verified": True, "token": f"SGR-DOC-OK-{random.randint(1000,9999)}"}
        ],
        "delay_guidance": {
            "delay_reason": "Application freshly submitted with all verified documents. In normal queue.",
            "required_action": "None. Waiting for departmental officer scrutiny.",
            "next_step": "Document scrutiny & milestone advancement by officer desk."
        },
        "esign": None
    }
    
    DATABASE["files"].insert(0, new_file)
    log_audit("SERVICE_SUBMISSION", f"Citizen: {applicant_name}", new_id, f"Application for {service['name']} submitted & paid via Razorpay (₹{service['fee']}).")
    trigger_webhook_event("NEW_SERVICE_APPLICATION", new_file, f"Application created. Paid via Razorpay ({payment_ref}). Income Tax & UIDAI verified.")
    
    return RedirectResponse(url=f"/citizen?search_id={new_id}&success=true", status_code=303)

# ================= OFFICER DESK =================
@app.get("/officer", response_class=HTMLResponse)
async def officer_dashboard(request: Request, officer_id: str = "OFF-103"):
    officer = next((o for o in DATABASE["officers"] if o["id"] == officer_id), DATABASE["officers"][0])
    
    dept_files = [f for f in DATABASE["files"] if f.get("department") == officer["department"]]
    enriched_files = [enrich_file_with_prediction(f) for f in dept_files]
    sorted_files = sorted(enriched_files, key=lambda x: x["prediction"]["delay_risk_pct"], reverse=True)
    
    return templates.TemplateResponse(
        request=request,
        name="officer.html",
        context={
            "user_role": "officer",
            "current_officer": officer,
            "officers": DATABASE["officers"],
            "files": sorted_files,
            "stages": STAGES
        }
    )

@app.post("/officer/update-stage")
async def officer_update_stage(
    file_id: str = Form(...),
    new_stage: str = Form(None),
    officer_notes: str = Form(""),
    officer_id: str = Form("OFF-103")
):
    target_file = next((f for f in DATABASE["files"] if f["id"] == file_id), None)
    if target_file:
        old_stage = target_file["current_stage"]
        if not new_stage or new_stage == old_stage:
            try:
                curr_idx = STAGES.index(old_stage)
                next_idx = min(curr_idx + 1, len(STAGES) - 1)
                calculated_stage = STAGES[next_idx]
            except ValueError:
                calculated_stage = STAGES[1]
        else:
            calculated_stage = new_stage

        target_file["current_stage"] = calculated_stage
        target_file["days_in_current_stage"] = 0
        target_file["status"] = "IN_PROGRESS"
        
        log_audit("STAGE_ADVANCED", f"Officer ID: {officer_id}", file_id, f"Stage advanced from {old_stage} to {calculated_stage}. Notes: {officer_notes}")
        trigger_webhook_event("WORKFLOW_STAGE_UPDATE", target_file, f"Progressed to {calculated_stage}. Notification dispatched to citizen.")
        
    return RedirectResponse(url=f"/officer?officer_id={officer_id}&updated=true", status_code=303)

# ================= DIGITAL E-SIGN EXECUTION (Final Officer) =================
@app.post("/officer/execute-esign")
async def execute_digital_esign(
    file_id: str = Form(...),
    officer_id: str = Form(...),
    dsc_pin: str = Form(...)
):
    target_file = next((f for f in DATABASE["files"] if f["id"] == file_id), None)
    officer = next((o for o in DATABASE["officers"] if o["id"] == officer_id), DATABASE["officers"][0])
    
    if target_file:
        cert_hash = hashlib.sha256(f"{file_id}_{officer['name']}_{datetime.now()}".encode()).hexdigest()[:24]
        target_file["current_stage"] = "DISPATCH_DIGILOCKER"
        target_file["status"] = "COMPLETED"
        target_file["esign"] = {
            "signed_by": officer["name"],
            "designation": officer["designation"],
            "timestamp": datetime.now().strftime("%d %b %Y, %H:%M:%S IST"),
            "cert_hash": cert_hash,
            "status": "OFFICIALLY_ISSUED"
        }
        target_file["delay_guidance"] = {
            "delay_reason": "Service completed & officially E-Signed.",
            "required_action": "Download your official certificate from the citizen portal or DigiLocker.",
            "next_step": "Service Delivered."
        }
        
        log_audit("ESIGN_ISSUED", f"Officer: {officer['name']}", file_id, f"Digital E-Signature applied. Certificate issued ({cert_hash}).")
        trigger_webhook_event("CERTIFICATE_ESIGNED_DISPATCHED", target_file, f"Official Sanction Order E-Signed by {officer['name']}. Sent to WhatsApp/SMS (+91 {target_file['applicant_phone']}) & DigiLocker.")
        
    return RedirectResponse(url=f"/officer?officer_id={officer_id}&signed=true", status_code=303)

# ================= CERTIFICATE VIEWER / DOWNLOAD =================
@app.get("/certificate/{file_id}", response_class=HTMLResponse)
async def view_certificate(request: Request, file_id: str):
    target_file = next((f for f in DATABASE["files"] if f["id"] == file_id), DATABASE["files"][0])
    return templates.TemplateResponse(
        request=request,
        name="certificate.html",
        context={"request": request, "file": target_file}
    )

# ================= DEPARTMENT HEAD & ADMIN =================
@app.get("/dept-head", response_class=HTMLResponse)
async def dept_head_dashboard(request: Request):
    files = [enrich_file_with_prediction(f) for f in DATABASE["files"]]
    return templates.TemplateResponse(
        request=request,
        name="dept_head.html",
        context={
            "user_role": "officer",
            "departments": DATABASE["departments"],
            "officers": DATABASE["officers"],
            "files": files,
            "total_files": len(files),
            "critical_files": len([f for f in files if f["prediction"]["risk_category"] == "CRITICAL"]),
            "moderate_files": len([f for f in files if f["prediction"]["risk_category"] == "MODERATE"]),
            "on_track_files": len([f for f in files if f["prediction"]["risk_category"] == "LOW"]),
            "bottlenecks": {}
        }
    )

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "user_role": "officer",
            "departments": DATABASE["departments"],
            "officers": DATABASE["officers"],
            "webhook_logs": DATABASE["webhook_logs"],
            "audit_logs": DATABASE["audit_logs"]
        }
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
