import os
import re
from io import BytesIO
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI
import PyPDF2

from skills_config import TECH_SKILLS, aggregate_skill_demand, match_cv_skills
from docx_utils import create_docx

load_dotenv(override=True)


def get_env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


SUPABASE_URL = get_env("SUPABASE_URL")
SUPABASE_KEY = get_env("SUPABASE_KEY")
OPENAI_API_KEY = get_env("OPENAI_API_KEY")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️ Αποτυχία σύνδεσης Supabase: {e}")

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = FastAPI(title="AI Job Market Analyzer API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def fetch_jobs():
    if not supabase:
        return []
    try:
        res = supabase.table("job_postings").select("*").execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Σφάλμα Supabase: {e}")


# ------------------------------------------------------------------
# API
# ------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"supabase_connected": supabase is not None, "openai_connected": openai_client is not None}


@app.get("/api/jobs")
def get_jobs(skill: Optional[str] = None):
    jobs = fetch_jobs()
    if skill and skill.lower() != "all":
        pattern = re.compile(rf"\b{re.escape(skill)}\b", re.IGNORECASE)
        jobs = [j for j in jobs if pattern.search(j.get("description") or "")]
    return {"count": len(jobs), "jobs": jobs}


@app.get("/api/skills-demand")
def skills_demand():
    jobs = fetch_jobs()
    descriptions = [j.get("description", "") for j in jobs]
    counts = aggregate_skill_demand(descriptions, TECH_SKILLS)
    data = [{"skill": k, "demand": v} for k, v in counts.items()]
    data.sort(key=lambda x: x["demand"], reverse=True)
    return {"total_jobs": len(jobs), "skills": data}


def _extract_pdf_text(file_bytes: bytes) -> str:
    reader = PyPDF2.PdfReader(BytesIO(file_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


@app.post("/api/cv/parse")
async def parse_cv(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Μόνο PDF αρχεία υποστηρίζονται.")
    content = await file.read()
    try:
        text = _extract_pdf_text(content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Σφάλμα ανάγνωσης PDF: {e}")
    if not text:
        raise HTTPException(status_code=422, detail="Δεν βρέθηκε επιλέξιμο κείμενο (πιθανώς σαρωμένη εικόνα).")

    market = skills_demand()
    max_demand = max((s["demand"] for s in market["skills"]), default=0) or 1
    demand_by_skill = {s["skill"]: s["demand"] for s in market["skills"]}
    user_skills = match_cv_skills(text, TECH_SKILLS)

    radar = [
        {
            "skill": s,
            "market": round(demand_by_skill.get(s, 0) / max_demand, 3),
            "cv": user_skills[s],
        }
        for s in TECH_SKILLS
    ]
    return {"text": text, "radar": radar}


class CvTextRequest(BaseModel):
    cv_text: str


@app.post("/api/cv/feedback")
def cv_feedback(req: CvTextRequest):
    if not openai_client:
        raise HTTPException(status_code=503, detail="Δεν έχει ρυθμιστεί OPENAI_API_KEY στον server.")
    prompt = (
        f"Ανάλυσε το CV: {req.cv_text[:2500]}. "
        f"Ζητούμενα skills: {', '.join(TECH_SKILLS)}. "
        "Δώσε: 1. Match Score (%) 2. Δυνατά σημεία (2-3 bullets) "
        "3. Τι λείπει (2-3 bullets). Σύντομα, στα Ελληνικά."
    )
    try:
        res = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return {"feedback": res.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Σφάλμα OpenAI: {e}")


@app.post("/api/cv/cover-letter")
def cv_cover_letter(req: CvTextRequest):
    if not openai_client:
        raise HTTPException(status_code=503, detail="Δεν έχει ρυθμιστεί OPENAI_API_KEY στον server.")
    prompt = (
        "Γράψε επαγγελματικό Cover Letter στα Ελληνικά για θέση Data/AI, "
        f"βασισμένο στο εξής CV: {req.cv_text[:2500]}"
    )
    try:
        res = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return {"cover_letter": res.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Σφάλμα OpenAI: {e}")


class DocxRequest(BaseModel):
    title: str
    content: str
    doc_type: str = "Document"
    filename: str = "report.docx"


@app.post("/api/report/docx")
def report_docx(req: DocxRequest):
    buf = create_docx(req.title, req.content, req.doc_type)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{req.filename}"'},
    )


# ------------------------------------------------------------------
# Static frontend
# ------------------------------------------------------------------
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")