# 🇮🇳 Civiora - Intelligent File Verification & Workflow Delay Detection System
**Smart India Hackathon (SIH 2026)**
*Theme: Smart Automation • Ministry of Personnel, Public Grievances and Pensions*

---

## 📦 How to Run on Any PC (Quick 2-Step Setup)

### Prerequisites:
- Install **Python 3.10+** (Make sure to check *"Add python.exe to PATH"* during installation).

---

### Option 1: 1-Click Launch (Windows)
1. Double-click the **`start_portal.bat`** file inside this folder.
2. It will automatically install any missing dependencies and start the server.
3. Open your browser and go to: **`http://127.0.0.1:8000`**

---

### Option 2: Manual Terminal Launch
1. Open Command Prompt (`cmd`) or PowerShell in this folder.
2. Install the required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```
   *(or `python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload`)*
4. Open your browser at: **`http://127.0.0.1:8000`**

---

## 🔑 Demo Access Credentials

### 1. Citizen Portal
- **Login Flow**: Click **Citizen** on Home -> Enter any 10-digit mobile number -> Enter Demo OTP: **`123456`**.
- **Features**: Multi-step service application wizard, dynamic checklist, document upload, DigiLocker KYC verification, smart correctness check, actionable re-upload flow, fee payment, and real-time tracking with AI delay predictions.

### 2. Government Officer Desk
- **Login Flow**: Click **Government Officer** on Home -> Enter credentials:
  - **Municipal Officer**: Login ID: `OFF-103` | Dept: `MUNICIPAL` | Password: `gov@2026`
  - **Pension Officer**: Login ID: `OFF-101` | Dept: `PENSION` | Password: `gov@2026`
  - **Revenue Officer**: Login ID: `OFF-102` | Dept: `REVENUE` | Password: `gov@2026`
  - **Education Desk**: Login ID: `OFF-104` | Dept: `EDUCATION` | Password: `gov@2026`
- **Features**: Strictly department-isolated priority queue, step-by-step milestone progression, and signed HMAC Webhook dispatches.
