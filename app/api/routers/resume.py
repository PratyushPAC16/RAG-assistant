from __future__ import annotations

import json
import logging
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.dependencies import _sanitize_filename

router = APIRouter(tags=["Career Intelligence"])
logger = logging.getLogger(__name__)

_ANALYSIS_SYSTEM_PROMPT = """You are an ATS (Applicant Tracking System) and Career Intelligence Agent.
Compare the provided Resume text and Job Description text.

Extract the following details and perform a comparison:
1. Skills present in the resume.
2. Projects mentioned in the resume.
3. Education history from the resume.
4. Experience history from the resume.
5. Job Description requirements (skills, experience, education).
6. Strengths of the candidate relative to the JD.
7. Weaknesses of the candidate relative to the JD.
8. Suggestions for improvement to make the resume stand out or prepare for the interview.

Perform scoring:
- Match Score (0 to 100) based on overall fit.
- Skill Match % (0 to 100) based on key technologies/skills match.
- Project Match % (0 to 100) based on relevance of projects.
- Experience Match % (0 to 100) based on job history alignment.
- Education Match % (0 to 100) based on degree/major requirements match.
- Keyword Match % (0 to 100) based on target vocabulary.
- Formatting Score % (0 to 100) based on resume layout (clarity, section divisions, lack of parsing errors).

Perform missing skills classification:
- Critical (must-have skills missing in the resume but highly emphasized in the JD).
- Recommended (should-have skills missing in the resume).
- Optional (nice-to-have skills missing in the resume).

Perform keyword analysis:
- Extract top keywords from the JD (minimum 4).
- Extract top keywords from the Resume (minimum 4).
- Identify missing keywords (minimum 3).
- Calculate keyword coverage % (0 to 100).

Perform interview readiness assessment:
- Calculate an Interview Readiness Score (0 to 100).
- Assign a status: "Likely Shortlisted" (score 75+), "Borderline" (score 60-74), or "Needs Improvement" (score <60).

CRITICAL GUIDELINES FOR EXTRACTION:
- You MUST analyze the candidate's actual Resume text and Job Description text. Do NOT use the example values from the JSON template below.
- "extracted_education": Extract the candidate's actual highest degree(s), school/university, major(s), and graduation year from their Resume (e.g., "B.Tech in Electronics and Communication Engineering from Indian Institute of Information Technology Dharwad (2023 - 2027)"). Do NOT copy "MS in CS from Stanford University". If not found, output "Not specified in resume".
- "extracted_experience": Extract the candidate's actual professional work history or a summary of their career background from their Resume (e.g., "Intern at X", "Freelance developer", or "No formal experience" if they only have academic projects). Do NOT copy "3 years as a Software Engineer at Google". If not found, output "Not specified in resume".
- All scores, missing skills, projects, and insights must be derived dynamically from the real input text.

You MUST respond with a single valid JSON object containing the exact keys listed below:
{
  "match_score": 84,
  "skill_match_pct": 88,
  "project_match_pct": 82,
  "experience_match_pct": 79,
  "education_match_pct": 95,
  "keyword_match_pct": 76,
  "formatting_score": 90,
  "extracted_skills": [
    {"name": "Python", "present": true},
    {"name": "LangGraph", "present": false}
  ],
  "extracted_projects": ["Project A: built a RAG app...", "Project B: ..."],
  "extracted_education": "<EXTRACT AND INSERT ACTUAL EDUCATION FROM RESUME TEXT HERE>",
  "extracted_experience": "<EXTRACT AND INSERT ACTUAL EXPERIENCE/WORK HISTORY FROM RESUME TEXT HERE>",
  "jd_requirements": ["Degree in CS", "Experience with RAG", "Knowledge of ChromaDB"],
  "missing_skills_categorized": {
    "critical": ["LangGraph", "Kubernetes"],
    "recommended": ["CI/CD", "AWS"],
    "optional": ["Docker", "Git"]
  },
  "keyword_analysis": {
    "top_jd_keywords": [{"text": "Kubernetes", "value": 8}, {"text": "LangGraph", "value": 6}],
    "top_resume_keywords": [{"text": "Python", "value": 10}, {"text": "RAG", "value": 5}],
    "missing_keywords": ["Kubernetes", "CI/CD"],
    "keyword_coverage_pct": 76
  },
  "recruiter_insights": {
    "strengths": ["Strong Python experience", "Relevant AI projects"],
    "weaknesses": ["Missing deployment experience", "Limited cloud keywords"],
    "improvement_suggestions": ["Add Kubernetes setup to Project A", "Study LangGraph routing schemas"]
  },
  "interview_readiness": {
    "score": 78,
    "status": "Likely Shortlisted"
  }
}

Respond ONLY with the raw JSON. Do not include markdown code fences, notes, or explanations outside the JSON."""


@router.post(
    "/analyze-resume",
    summary="Analyze resume against job description",
)
async def analyze_resume(
    resume: UploadFile = File(...),
    jd: UploadFile = File(...)
) -> dict:
    """
    Compare a candidate's resume PDF against a job description PDF.
    Extracts skills, education, experience, projects, and calculates match scores.
    """
    from app.utils.pdf_extractor import extract_text_from_pdf
    from app.utils.llm_factory import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage

    # Validate file extensions after sanitization
    for f in (resume, jd):
        filename = _sanitize_filename(f.filename or "")
        ext = Path(filename).suffix.lower().lstrip(".")
        if ext != "pdf":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Only PDF files are supported. Uploaded file is '.{ext}'"
            )

    try:
        # Extract text from both files
        resume_bytes = await resume.read()
        jd_bytes = await jd.read()
        
        resume_text = extract_text_from_pdf(resume_bytes)
        jd_text = extract_text_from_pdf(jd_bytes)

        if not resume_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to extract readable text from Resume PDF."
            )
        if not jd_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to extract readable text from Job Description PDF."
            )

        # Assemble prompt for LLM comparison
        prompt = f"RESUME TEXT:\n{resume_text}\n\nJOB DESCRIPTION TEXT:\n{jd_text}"
        messages = [
            SystemMessage(content=_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]

        llm = get_llm(temperature=0.1)
        response = llm.invoke(messages)
        content = response.content.strip()

        # Clean code fences
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        analysis_result = json.loads(content)
        return analysis_result

    except Exception as exc:
        logger.error("Resume analysis failed", extra={"error": str(exc)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Resume analysis failed. Check server logs for details."
        )
