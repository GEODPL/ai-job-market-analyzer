"""Semantic matching: CV embedding έναντι embeddings πραγματικών αγγελιών."""
import math

EMBEDDING_MODEL = "text-embedding-3-small"

# In-process cache: job_id -> embedding vector.
# Αρκεί για single-process deployment (π.χ. uvicorn χωρίς πολλαπλά workers).
# Αν αργότερα τρέχεις πολλά workers/instances, θα χρειαστεί persistent cache
# (π.χ. πίνακας στο Supabase) αντί για in-memory dict.
_job_embedding_cache: dict[str, list[float]] = {}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _embed_batch(openai_client, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    res = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in res.data]


def embed_cv(openai_client, cv_text: str) -> list[float]:
    return _embed_batch(openai_client, [cv_text[:4000]])[0]


def get_job_embeddings(openai_client, jobs: list[dict]) -> dict[str, list[float]]:
    """Επιστρέφει {job_id: embedding}. Κάνει embed ΜΟΝΟ τις αγγελίες που
    δεν έχουμε ήδη στο cache -> γλιτώνει επαναλαμβανόμενα OpenAI calls."""
    missing = [j for j in jobs if j.get("job_id") and j["job_id"] not in _job_embedding_cache]

    batch_size = 100  # OpenAI embeddings API δέχεται πολλαπλά inputs ανά call
    for i in range(0, len(missing), batch_size):
        chunk = missing[i:i + batch_size]
        texts = [f"{j.get('title', '')}. {j.get('description', '')[:2000]}" for j in chunk]
        embeddings = _embed_batch(openai_client, texts)
        for job, emb in zip(chunk, embeddings):
            _job_embedding_cache[job["job_id"]] = emb

    return {
        j["job_id"]: _job_embedding_cache[j["job_id"]]
        for j in jobs
        if j.get("job_id") in _job_embedding_cache
    }


def match_jobs_to_cv(openai_client, cv_text: str, jobs: list[dict], top_n: int = 5) -> list[dict]:
    if not jobs:
        return []

    cv_embedding = embed_cv(openai_client, cv_text)
    job_embeddings = get_job_embeddings(openai_client, jobs)

    scored = []
    for job in jobs:
        emb = job_embeddings.get(job.get("job_id"))
        if emb is None:
            continue
        raw_score = _cosine_similarity(cv_embedding, emb)
        scored.append({
            "job_id": job.get("job_id"),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "url": job.get("url", ""),
            "category": job.get("category", ""),
            "raw_score": raw_score,
        })

    if not scored:
        return []

    # Το ακατέργαστο cosine similarity ανάμεσα σε CV και αγγελία σπάνια ξεπερνάει
    # ~0.5-0.6 ακόμα και για άριστο match (διαφορετική δομή/μήκος κειμένου), οπότε
    # ως raw % παραπλανεί. Κάνουμε min-max normalize μέσα στη ΣΥΝΟΛΙΚΗ δεξαμενή
    # αγγελιών -> δείχνει σχετική ταύτιση ("πόσο καλύτερο είναι αυτό vs τα υπόλοιπα
    # διαθέσιμα αυτή τη στιγμή"), πιο διαισθητικό και τίμιο ως ποσοστό.
    raw_values = [s["raw_score"] for s in scored]
    lo, hi = min(raw_values), max(raw_values)
    span = hi - lo
    for s in scored:
        s["score"] = round((s["raw_score"] - lo) / span, 4) if span > 1e-9 else 1.0
        del s["raw_score"]

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


def clear_cache():
    _job_embedding_cache.clear()