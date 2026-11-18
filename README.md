# Recruiting Assistant

A Streamlit app for structured, job-relevant resume review. It supports individual PDF matching and shortlisting PDFs from a Google Drive folder. Treat its output as decision support only: a person must review each candidate using consistent, job-related criteria.

## Run locally

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create local settings:

   ```bash
   cp .env.example .env
   ```

3. Set `OPENAI_API_KEY` in `.env`, then run:

   ```bash
   streamlit run streamlit_app.py
   ```

## Deploy to Streamlit Community Cloud

1. Push this repository **without** `.env`, `.venv`, or `secrets/`.
2. In Streamlit Community Cloud, create an app from this repository, select the `main` branch, and set the entrypoint to `streamlit_app.py`.
3. In the app's **Secrets** settings, add:

   ```toml
   OPENAI_API_KEY = "..."
   OPENAI_MODEL = "gpt-4o-mini"
   MAX_RESUME_MB = "10"
   MAX_DRIVE_FILES = "25"
   MAX_INPUT_CHARS = "20000"
   APP_PASSWORD = "use-a-long-unique-password"
   ```

4. If Google Drive shortlisting is needed, add the entire service-account JSON as an escaped string:

   ```toml
   GOOGLE_SERVICE_ACCOUNT_JSON = '{"type":"service_account", ...}'
   ```

   Enable the Google Drive API, then share only the intended resume folder with that service account's email address. Do not store Google OAuth files in the repository or Streamlit app.

`APP_PASSWORD` protects the public Streamlit URL. Keep it set for deployed apps and rotate it with the other secrets when access changes.

## Safeguards

- Uploaded resumes and Drive downloads use temporary files and are not retained.
- File counts, file sizes, and prompt inputs are limited to reduce unexpected cost and failures.
- The Streamlit app requires a separate secret for its access password when deployed.
- Never use an automated score as the sole or final employment decision.

## Optional Docker deployment

The existing FastAPI and Docker Compose configuration remains available for self-hosted deployments. See [`deployment/aws/README.md`](deployment/aws/README.md) for the ECS path.
