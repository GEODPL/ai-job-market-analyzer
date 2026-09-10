
import re

TECH_SKILLS = [
    "Python", "SQL", "AWS", "Machine Learning", "NLP",
    "LLM", "RAG", "Pandas", "PyTorch", "Docker",
]


def skill_present(text: str, skill: str) -> bool:
    if not text:
        return False
    pattern = rf"\b{re.escape(skill.lower())}\b"
    return bool(re.search(pattern, text.lower()))


def aggregate_skill_demand(descriptions, skills=None) -> dict:
    skills = skills or TECH_SKILLS
    counts = {s: 0 for s in skills}
    for desc in descriptions:
        text = (desc or "").lower()
        for s in skills:
            if skill_present(text, s):
                counts[s] += 1
    return counts


def match_cv_skills(cv_text: str, skills=None) -> dict:
    skills = skills or TECH_SKILLS
    return {s: (1 if skill_present(cv_text, s) else 0) for s in skills}