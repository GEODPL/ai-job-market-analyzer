# AI Job Market Analyzer (Greece)

FastAPI backend (Python) + καθαρό HTML/CSS/JS frontend (Tailwind + Chart.js, χωρίς build step). Ένα process σερβίρει και τα δύο.

## Δομή
```
backend/
  main.py            # FastAPI app + REST API + σερβίρει το frontend
  skills_config.py    # Κεντρική λίστα skills + matching
  docx_utils.py        # Δημιουργία .docx αναφορών
  etl_pipeline.py      # Φόρτωση demo αγγελιών στο Supabase
  analyze_skills.py    # CLI ανάλυση ζήτησης skills
  requirements.txt
frontend/
  index.html
  app.js
  styles.css
```

## Ρύθμιση
1. Δημιούργησε `backend/.env`:
```
SUPABASE_URL=...
SUPABASE_KEY=...
OPENAI_API_KEY=...
```

2. Εγκατάσταση εξαρτήσεων:
```bash
cd backend
pip install -r requirements.txt --break-system-packages
```

3.  Φόρτωσε demo δεδομένα στο Supabase:
```bash
python etl_pipeline.py
```

4. Τρέξε τον server:
```bash
uvicorn main:app --reload
```

5. Άνοιξε το browser στο **http://localhost:8000** — θα δεις το site , που καλεί το FastAPI backend στο `/api/*`.

## API endpoints
- `GET  /api/health`
- `GET  /api/jobs?skill=Python`
- `GET  /api/skills-demand`
- `POST /api/cv/parse`  (multipart form, field `file`)
- `POST /api/cv/feedback`  (json `{cv_text}`)
- `POST /api/cv/cover-letter`  (json `{cv_text}`)
- `POST /api/report/docx`  (json `{title, content, doc_type, filename}`) → επιστρέφει .docx αρχείο
