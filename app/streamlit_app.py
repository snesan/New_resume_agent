import os
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import streamlit as st
from dotenv import load_dotenv

from app.google_drive import DriveConfigurationError, DriveFolderError, download_folder_from_drive
from app.recruiter import AgentConfigurationError, RecruiterAgent


load_dotenv()


def _secret_or_env(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name)
    except FileNotFoundError:
        value = None
    return str(value if value is not None else os.getenv(name, default))


def _configure_environment() -> None:
    for name in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "MAX_RESUME_MB",
        "MAX_DRIVE_FILES",
        "MAX_INPUT_CHARS",
    ):
        value = _secret_or_env(name)
        if value:
            os.environ[name] = value


def _setting_as_int(name: str, default: int) -> int:
    try:
        return max(1, int(_secret_or_env(name, str(default))))
    except ValueError:
        return default


def _require_password() -> bool:
    password = _secret_or_env("APP_PASSWORD")
    if not password:
        return True
    if st.session_state.get("authenticated"):
        return True

    st.title("Recruiting Assistant")
    with st.form("sign-in"):
        supplied_password = st.text_input("Access password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        if supplied_password == password:
            st.session_state.authenticated = True
            st.rerun()
        st.error("Incorrect password.")
    return False


@st.cache_resource
def _get_agent() -> RecruiterAgent:
    return RecruiterAgent()


def _validate_job_description(job_description: str, max_input_chars: int) -> bool:
    if not job_description.strip():
        st.warning("Provide a job description.")
        return False
    if len(job_description) > max_input_chars:
        st.warning(f"Keep the job description below {max_input_chars:,} characters.")
        return False
    return True


def _evaluate_upload(agent: RecruiterAgent, job_description: str, uploaded_file, max_bytes: int):
    content = uploaded_file.getvalue()
    if len(content) > max_bytes:
        raise ValueError(f"Resume exceeds the {max_bytes // (1024 * 1024)} MB upload limit.")
    with NamedTemporaryFile(suffix=".pdf") as temporary_resume:
        temporary_resume.write(content)
        temporary_resume.flush()
        return agent.match_single_resume(job_description, temporary_resume.name)


def run() -> None:
    st.set_page_config(page_title="Recruiting Assistant", page_icon="🤖", layout="wide")
    _configure_environment()
    if not _require_password():
        return

    max_resume_bytes = _setting_as_int("MAX_RESUME_MB", 10) * 1024 * 1024
    max_drive_files = _setting_as_int("MAX_DRIVE_FILES", 25)
    max_input_chars = _setting_as_int("MAX_INPUT_CHARS", 20_000)
    agent = _get_agent()

    st.title("🤖 Recruiting Assistant")
    st.caption("Use results as decision support only; review candidates using consistent, job-relevant criteria.")
    single_tab, drive_tab = st.tabs(["📋 Single Resume Match", "📁 Google Drive Shortlist"])

    with single_tab:
        st.header("Match a Resume with a Job Description")
        job_description = st.text_area("Job Description", height=220, key="single_jd")
        resume_file = st.file_uploader("Resume PDF", type=["pdf"], accept_multiple_files=False)
        st.caption("The uploaded PDF is processed for this request and is not retained.")

        if st.button("Evaluate Match", type="primary"):
            if resume_file is None or not _validate_job_description(job_description, max_input_chars):
                if resume_file is None:
                    st.warning("Provide a PDF resume.")
            else:
                try:
                    with st.spinner("Evaluating the resume..."):
                        result = _evaluate_upload(agent, job_description, resume_file, max_resume_bytes)
                    st.metric("Match Score", f"{result['match_score']}%")
                    st.json(result)
                except (AgentConfigurationError, ValueError) as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("The resume could not be evaluated. Check the PDF and try again.")

    with drive_tab:
        st.header("Shortlist PDFs from Google Drive")
        drive_job_description = st.text_area("Job Description", height=220, key="drive_jd")
        drive_folder_id = st.text_input("Google Drive Folder ID or URL")
        st.caption(f"Up to {max_drive_files} PDF files are evaluated per request.")

        if st.button("Run Batch Shortlisting"):
            if not drive_folder_id.strip() or not _validate_job_description(drive_job_description, max_input_chars):
                if not drive_folder_id.strip():
                    st.warning("Provide a Google Drive folder ID or URL.")
            else:
                try:
                    with st.spinner("Downloading and evaluating resumes..."):
                        with TemporaryDirectory(prefix="resumes-") as temporary_directory:
                            files = download_folder_from_drive(
                                drive_folder_id,
                                temporary_directory,
                                max_files=max_drive_files,
                                max_file_bytes=max_resume_bytes,
                            )
                            results = agent.shortlist_resumes(drive_job_description, files)
                    st.success(f"Evaluated {len(results)} candidates.")
                    for index, candidate in enumerate(results, start=1):
                        label = f"Rank #{index}: {candidate['filename']} — {candidate['score']}%"
                        with st.expander(label):
                            if "error" in candidate:
                                st.error("This resume could not be evaluated.")
                            else:
                                st.json(candidate["details"])
                except (AgentConfigurationError, DriveConfigurationError, DriveFolderError, ValueError) as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("The Drive folder could not be processed. Verify access and try again.")
