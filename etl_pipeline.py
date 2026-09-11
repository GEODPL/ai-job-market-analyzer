import os
import re
import html
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Φόρτωση κλειδιών
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
APIFY_TOKEN: str = os.environ.get("APIFY_API_TOKEN")

# Apify actor "kariera-gr-scraper" (studio-amba) - πραγματικές, ενεργές αγγελίες
# από το kariera.gr, multi-industry (όχι μόνο tech), με πραγματική κατηγοριοποίηση.
# https://apify.com/studio-amba/kariera-gr-scraper
ACTOR_ID = "studio-amba~kariera-gr-scraper"
APIFY_RUN_URL = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"

supabase: Client | None = None
try:
    if url and key:
        supabase = create_client(url, key)
    else:
        print("⚠️ Προειδοποίηση: Δεν βρέθηκαν τα κλειδιά Supabase στο .env.")
except Exception as e:
    print(f"❌ Σφάλμα σύνδεσης Supabase: {e}")


def _strip_html(raw_html: str) -> str:
    """Αφαιρεί HTML tags από την περιγραφή που επιστρέφει ο scraper."""
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _first(job: dict, *keys):
    """Επιστρέφει την πρώτη μη-κενή τιμή ανάμεσα σε πιθανά ονόματα πεδίων.
    Ο scraper μπορεί να ονοματίζει διαφορετικά τα ίδια δεδομένα ανάλογα την
    έκδοση του actor -> προσπαθούμε αρκετές παραλλαγές αμυντικά."""
    for k in keys:
        v = job.get(k)
        if v not in (None, "", []):
            return v
    return None


def fetch_greek_jobs(search_query: str = "", max_results: int = 150):
    """
    Αντλεί πραγματικές, ενεργές αγγελίες από το kariera.gr (multi-industry)
    μέσω του Apify actor 'studio-amba/kariera-gr-scraper'.

    search_query="" -> browse τις πιο πρόσφατες αγγελίες σε όλους τους κλάδους
    (marketing, sales, healthcare, tech, κλπ) - όχι μόνο Data/AI.

    Χρειάζεται APIFY_API_TOKEN στο .env (δωρεάν account στο apify.com).
    """
    if not APIFY_TOKEN:
        print("❌ Λείπει το APIFY_API_TOKEN στο .env. Δες README για οδηγίες.")
        return []

    print(f"📥 Άντληση πραγματικών αγγελιών από kariera.gr (έως {max_results})...")

    payload = {
        "searchQuery": search_query,
        "maxResults": max_results,
        "fetchDetails": True,
    }

    try:
        resp = requests.post(
            APIFY_RUN_URL,
            params={"token": APIFY_TOKEN},
            json=payload,
            timeout=180,
        )
        resp.raise_for_status()
        raw_jobs = resp.json()
    except Exception as e:
        print(f"❌ Σφάλμα κλήσης Apify actor: {e}")
        return []

    if raw_jobs:
        print(f"ℹ️  Διαθέσιμα πεδία στο πρώτο αποτέλεσμα: {sorted(raw_jobs[0].keys())}")

    jobs = []
    for job in raw_jobs:
        description = _strip_html(job.get("descriptionHtml", ""))
        if not description:
            description = ", ".join(job.get("tags", []) or [])

        salary_min = _first(job, "salaryMin", "salary_min", "minSalary")
        salary_max = _first(job, "salaryMax", "salary_max", "maxSalary")

        jobs.append({
            "job_id": str(job.get("jobId") or job.get("url", ""))[:64],
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "description": description,
            "url": job.get("url", ""),
            "posted_at": job.get("publishedAt", ""),
            "category": job.get("category", "") or "",
            "location": job.get("location", "") or "",
            "employment_type": job.get("employmentType", "") or "",
            "remote": _first(job, "remote", "remoteType", "workType", "remoteWork") or "",
            "seniority": _first(job, "seniority", "seniorityLevel", "experienceLevel") or "",
            "salary_min": float(salary_min) if salary_min is not None else None,
            "salary_max": float(salary_max) if salary_max is not None else None,
            "salary_currency": _first(job, "salaryCurrency", "currency") or "EUR",
        })

    print(f"✅ Βρέθηκαν {len(jobs)} πραγματικές αγγελίες.")
    return jobs


def load_to_supabase(records):
    if not supabase:
        print("❌ Δεν υπάρχει σύνδεση με το Supabase.")
        return
    if not records:
        print("⚠️ Καμία εγγραφή προς αποθήκευση (κενό αποτέλεσμα scraping).")
        return

    print("💾 Αποθήκευση αγγελιών στη βάση δεδομένων...")

    # Καθαρίζουμε τον πίνακα πρώτα για να μην μπλέκονται παλιές και νέες
    try:
        supabase.table('job_postings').delete().neq('job_id', '0').execute()
    except Exception as e:
        print(f"❌ Σφάλμα κατά τον καθαρισμό του πίνακα: {e}")
        return

    # Ανεβάζουμε τις νέες ελληνικές
    try:
        response = supabase.table('job_postings').upsert(records).execute()
        saved = len(response.data) if response.data else 0
        print(f"✅ Επιτυχία! Αποθηκεύτηκαν {saved} αγγελίες.")
    except Exception as e:
        print(f"❌ Σφάλμα κατά την αποθήκευση: {e}")


if __name__ == "__main__":
    jobs = fetch_greek_jobs(search_query="", max_results=150)
    load_to_supabase(jobs)