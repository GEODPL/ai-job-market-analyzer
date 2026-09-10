import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Φόρτωση κλειδιών
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

supabase: Client | None = None
try:
    if url and key:
        supabase = create_client(url, key)
    else:
        print("⚠️ Προειδοποίηση: Δεν βρέθηκαν τα κλειδιά Supabase στο .env.")
except Exception as e:
    print(f"❌ Σφάλμα σύνδεσης Supabase: {e}")


def fetch_greek_jobs():
    print("📥 Φόρτωση ελληνικών αγγελιών εργασίας (Data Science & AI)...")


    greek_jobs_data = [
        {
            "job_id": "gr_001",
            "title": "Junior Data Scientist",
            "company": "Athens Analytics Hub",
            "description": "Ζητείται Junior Data Scientist με άριστη γνώση Python, Pandas και SQL για ανάλυση δεδομένων πελατών. Επιθυμητή η εμπειρία σε Machine Learning models και scikit-learn.",
            "url": "https://example.com/job1",
            "posted_at": "2026-06-01T10:00:00Z"
        },
        {
            "job_id": "gr_002",
            "title": "NLP Engineer / LLM Developer",
            "company": "Hellenic AI Startups",
            "description": "Αναζητούμε NLP Engineer για την ανάπτυξη συστημάτων RAG και chatbots στα ελληνικά. Απαραίτητη η γνώση Python, LangChain, OpenAI APIs και Vector Databases (ChromaDB/Pinecone).",
            "url": "https://example.com/job2",
            "posted_at": "2026-06-02T11:30:00Z"
        },
        {
            "job_id": "gr_003",
            "title": "Data Analyst",
            "company": "Piraeus Maritime Tech",
            "description": "Ζητείται Data Analyst με ισχυρές βάσεις σε SQL, Python και οπτικοποίηση δεδομένων (PowerBI/Plotly). Θα συμμετέχετε σε ETL pipelines και business intelligence reports.",
            "url": "https://example.com/job3",
            "posted_at": "2026-06-03T09:15:00Z"
        },
        {
            "job_id": "gr_004",
            "title": "Machine Learning Engineer",
            "company": "Athens FinTech Solutions",
            "description": "Η εταιρεία μας αναζητά Machine Learning Engineer. Απαιτούνται δυνατές γνώσεις Python, PyTorch ή TensorFlow, καθώς και εμπειρία σε AWS cloud infrastructure και Docker.",
            "url": "https://example.com/job4",
            "posted_at": "2026-06-04T14:20:00Z"
        },
        {
            "job_id": "gr_005",
            "title": "AI Researcher / Linguist Technologist",
            "company": "Hellenic Text Analytics",
            "description": "Ιδανική θέση για απόφοιτους Γλωσσολογίας ή Πληροφορικής με ειδίκευση στην επεξεργασία φυσικής γλώσσας (NLP). Απαιτείται γνώση Python, tokenization και χειρισμός κειμένων.",
            "url": "https://example.com/job5",
            "posted_at": "2026-06-05T08:45:00Z"
        },
        {
            "job_id": "gr_006",
            "title": "Junior Python Developer & Data Engineer",
            "company": "CloudServices Greece",
            "description": "Ψάχνουμε άτομο για αυτοματοποίηση διαδικασιών ETL με Python, Pandas και SQL. Θα χτίσετε αγωγούς δεδομένων και θα συνδεθείτε με Supabase/PostgreSQL.",
            "url": "https://example.com/job6",
            "posted_at": "2026-06-06T12:00:00Z"
        }
    ]

    return greek_jobs_data


def load_to_supabase(records):
    if not supabase:
        print("❌ Δεν υπάρχει σύνδεση με το Supabase.")
        return

    print("💾 Αποθήκευση ελληνικών αγγελιών στη βάση δεδομένων...")

    
    try:
        supabase.table('job_postings').delete().neq('job_id', '0').execute()
    except Exception as e:
        print(f"❌ Σφάλμα κατά τον καθαρισμό του πίνακα: {e}")
        return

    
    try:
        response = supabase.table('job_postings').upsert(records).execute()
        saved = len(response.data) if response.data else 0
        print(f"✅ Επιτυχία! Αποθηκεύτηκαν {saved} ελληνικές αγγελίες.")
    except Exception as e:
        print(f"❌ Σφάλμα κατά την αποθήκευση: {e}")


if __name__ == "__main__":
    jobs = fetch_greek_jobs()
    load_to_supabase(jobs)