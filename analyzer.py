import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

from skills_config import TECH_SKILLS, aggregate_skill_demand

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


def analyze_skills():
    if not supabase:
        print("❌ Δεν υπάρχει σύνδεση με το Supabase.")
        return

    print("📥 Άντληση δεδομένων από τη βάση...")
    try:
        response = supabase.table('job_postings').select('description').execute()
        data = response.data
    except Exception as e:
        print(f"❌ Σφάλμα κατά την ανάκτηση δεδομένων: {e}")
        return

    if not data:
        print("⚠️ Δεν βρέθηκαν δεδομένα στη βάση.")
        return

    print("🔍 Ανάλυση κειμένων (NLP) για δεξιότητες...")

    descriptions = [job.get('description', '') for job in data]
    skill_counts = aggregate_skill_demand(descriptions, TECH_SKILLS)

    df_skills = pd.DataFrame(list(skill_counts.items()), columns=['Skill', 'Demand (Αριθμός Αγγελιών)'])
    df_skills = df_skills.sort_values(by='Demand (Αριθμός Αγγελιών)', ascending=False)

    print("\n🏆 Τα Top Skills που ζητάει η αγορά τώρα:")
    print(df_skills.to_string(index=False))


if __name__ == "__main__":
    analyze_skills()