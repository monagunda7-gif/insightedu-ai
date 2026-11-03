# InsightEdu AI — Explainable Academic Risk Prediction

A Streamlit mini-project prototype with separate administrator, teacher and student portals.

## Important security and deployment changes
- **No demo accounts or demo passwords are created or displayed.**
- On a fresh database, the first administrator is created only from private environment variables:
  - `INSIGHTEDU_ADMIN_USERNAME`
  - `INSIGHTEDU_ADMIN_PASSWORD` (minimum 12 characters)
- Teacher and student accounts must be created by an authenticated administrator/teacher. No default student password is supplied.
- Passwords are stored as PBKDF2-SHA256 hashes. Password creation/reset requires at least 12 characters.
- Academic numeric fields and ABL marks are range-validated.
- Assignment uploads are limited to 20 MB; missing stored files show an error rather than crashing the page.
- Local database and uploads are stored under `INSIGHTEDU_DATA_DIR` (defaults to `./data`). Keep this directory on persistent storage in hosted deployments.
- `.gitignore` excludes databases, uploaded data, virtual environments and local secrets.

## Run locally (Windows PowerShell)
1. Extract the ZIP and open the extracted folder in VS Code.
2. In the VS Code terminal, create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .venv\\Scripts\\Activate.ps1
   ```
3. Install runtime dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Set a private first-admin username and password in the current terminal session (choose your own values):
   ```powershell
   $env:INSIGHTEDU_ADMIN_USERNAME = "your-admin-username"
   $env:INSIGHTEDU_ADMIN_PASSWORD = "choose-a-long-unique-password"
   ```
5. Start the app:
   ```powershell
   python -m streamlit run app.py
   ```
6. Sign in with the username/password you configured. The first admin is created once. After creation, changing these environment variables does not reset the existing admin password; use **Change admin password** in the admin sidebar.

For later local runs, set the same environment variables again in the new terminal if the database does not yet contain an administrator. Once the admin exists, they are no longer needed for login.

## Deploy on Render with persistent storage
This project includes `render.yaml` for a Render web service with a persistent disk mounted at `/var/data`.

1. Push the project files to a GitHub repository. Do **not** upload `data/`, database files, student records, uploaded assignments, `.env`, or `.streamlit/secrets.toml`.
2. In Render, create a **Blueprint** from that repository and review the `insightedu-ai` web service.
3. Set the prompted `INSIGHTEDU_ADMIN_USERNAME` and `INSIGHTEDU_ADMIN_PASSWORD` values privately in Render. Use a unique password of at least 12 characters.
4. Deploy. The service uses `/var/data` for its SQLite database and assignment uploads; the persistent disk is required to retain these between deployments/restarts.
5. Use the HTTPS URL supplied by Render. Do not use real student data until your institution has approved the hosting, access controls, privacy notice and backup process.

The persistent disk in the included blueprint uses Render's paid Starter plan. A free ephemeral host is **not suitable** for this SQLite + uploaded-file design because local files can be lost on restart/redeploy. If you choose another host, configure a persistent mounted volume and set `INSIGHTEDU_DATA_DIR` to its mount path.

## Demo / model limitations
There are no demo users or seeded student records in a fresh database. Create an admin through the environment variables, then create teacher accounts and student records through the app.

The live risk estimate is an explainable **rule-based baseline**, not a trained or validated machine-learning model. The synopsis's target recall is not an achieved result. Do not use risk scores as the sole basis for academic decisions.

The ML training scaffold is optional and its dependencies are in `requirements-ml.txt`. It requires a representative, consented, labelled dataset and proper validation before use. Do not claim the current baseline is an ML prediction.

## Data and security notes before real college use
- Use HTTPS and strong, unique credentials; never commit secrets or database files to GitHub.
- Restrict repository and hosting access. Public app access does not make student records public by design, but the app is internet-accessible; protect accounts and use institution-approved data only.
- Configure backups for the persistent volume and test restoration.
- SQLite on one persistent disk is suitable for a small prototype/single instance, not a high-concurrency production college system. For production, migrate to managed PostgreSQL and object storage, add rate limiting/monitoring, account recovery, audit retention, and institutional security review.
- The rule-based risk score is illustrative. Have a human teacher review any concern.

## Account workflow
- Admin: creates/deactivates teacher accounts, resets teacher passwords, views a read-only student directory and changes their own password.
- Teacher: manages their own classes, students, academic records, attendance, assignments, ABL marks and SGPA history.
- Student: signs in with their USN and a teacher-issued password and views their own records only.

