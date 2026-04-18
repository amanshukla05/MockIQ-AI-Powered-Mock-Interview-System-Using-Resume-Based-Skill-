"""
AI Mock Interview System — Main Flask Application
Run: python app.py
Visit: http://localhost:5000
"""

import os
import json
import uuid
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify
)
from utils.resume_parser import extract_text_from_pdf, extract_text_from_txt
from utils.skill_extractor import extract_skills, DOMAIN_SKILLS
from utils.question_generator import generate_questions, generate_followup
from utils.evaluator import evaluate_answer
from utils.sentiment import detect_sentiment
from utils.report import build_report

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "interview-secret-key-change-in-prod")

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"pdf", "txt"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ─────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────
@app.route("/")
def index():
    session.clear()
    return render_template("index.html")


# ─────────────────────────────────────────────
# UPLOAD & SETUP
# ─────────────────────────────────────────────
@app.route("/upload", methods=["GET", "POST"])
def upload():
    domains = list(DOMAIN_SKILLS.keys())
    if request.method == "POST":
        name = request.form.get("name", "Candidate").strip()
        domain = request.form.get("domain", "Data Analyst")
        resume_text = ""

        # Handle file upload
        file = request.files.get("resume")
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit(".", 1)[1].lower()
            safe_name = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
            file.save(filepath)
            if ext == "pdf":
                resume_text = extract_text_from_pdf(filepath)
            else:
                resume_text = extract_text_from_txt(filepath)

        # Fallback: manual paste
        if not resume_text:
            resume_text = request.form.get("resume_text", "")

        if not resume_text.strip():
            return render_template(
                "upload.html", domains=domains,
                error="Please upload a resume or paste your resume text."
            )

        skills = extract_skills(resume_text, domain)
        session["name"] = name
        session["domain"] = domain
        session["resume_text"] = resume_text
        session["skills"] = skills

        return redirect(url_for("skills_preview"))

    return render_template("upload.html", domains=domains)


# ─────────────────────────────────────────────
# SKILLS PREVIEW
# ─────────────────────────────────────────────
@app.route("/skills")
def skills_preview():
    if "skills" not in session:
        return redirect(url_for("upload"))
    return render_template(
        "skills.html",
        name=session.get("name"),
        domain=session.get("domain"),
        skills=session.get("skills", [])
    )


# ─────────────────────────────────────────────
# START INTERVIEW — generate questions
# ─────────────────────────────────────────────
@app.route("/start-interview", methods=["POST"])
def start_interview():
    if "skills" not in session:
        return redirect(url_for("upload"))

    domain = session["domain"]
    skills = session["skills"]
    resume_text = session["resume_text"]

    questions = generate_questions(domain, skills, resume_text)
    session["questions"] = questions
    session["current_q"] = 0
    session["answers"] = []
    session["scores"] = []
    session["feedbacks"] = []
    session["sentiments"] = []
    session["followups_asked"] = []

    return redirect(url_for("interview"))


# ─────────────────────────────────────────────
# INTERVIEW PAGE
# ─────────────────────────────────────────────
@app.route("/interview")
def interview():
    if "questions" not in session:
        return redirect(url_for("upload"))

    questions = session["questions"]
    idx = session["current_q"]
    total = len(questions)

    if idx >= total:
        return redirect(url_for("result"))

    q = questions[idx]
    progress_pct = int((idx / total) * 100)

    return render_template(
        "interview.html",
        question=q,
        q_num=idx + 1,
        total=total,
        progress_pct=progress_pct,
        name=session.get("name"),
        domain=session.get("domain"),
        last_followup=session.get("last_followup", None)
    )


# ─────────────────────────────────────────────
# SUBMIT ANSWER (AJAX)
# ─────────────────────────────────────────────
@app.route("/submit-answer", methods=["POST"])
def submit_answer():
    if "questions" not in session:
        return jsonify({"error": "Session expired"}), 400

    data = request.get_json()
    answer = data.get("answer", "").strip()
    if not answer:
        return jsonify({"error": "Empty answer"}), 400

    idx = session["current_q"]
    questions = session["questions"]
    q = questions[idx]
    domain = session["domain"]

    # Evaluate
    evaluation = evaluate_answer(q["text"], answer, domain, q["type"])
    sentiment = detect_sentiment(answer)

    # Follow-up
    followup = generate_followup(q["text"], answer, domain)

    # Store in session
    answers = session.get("answers", [])
    scores = session.get("scores", [])
    feedbacks = session.get("feedbacks", [])
    sentiments = session.get("sentiments", [])

    answers.append(answer)
    scores.append(evaluation["score"])
    feedbacks.append(evaluation["feedback"])
    sentiments.append(sentiment)

    session["answers"] = answers
    session["scores"] = scores
    session["feedbacks"] = feedbacks
    session["sentiments"] = sentiments
    session["last_followup"] = followup
    session.modified = True

    return jsonify({
        "score": evaluation["score"],
        "feedback": evaluation["feedback"],
        "strengths": evaluation.get("strengths", []),
        "improvements": evaluation.get("improvements", []),
        "sentiment": sentiment,
        "followup": followup,
        "is_last": (idx + 1) >= len(questions)
    })


# ─────────────────────────────────────────────
# NEXT QUESTION
# ─────────────────────────────────────────────
@app.route("/next-question", methods=["POST"])
def next_question():
    if "questions" not in session:
        return redirect(url_for("upload"))
    session["current_q"] = session.get("current_q", 0) + 1
    session["last_followup"] = None
    session.modified = True

    if session["current_q"] >= len(session["questions"]):
        return redirect(url_for("result"))
    return redirect(url_for("interview"))


# ─────────────────────────────────────────────
# RESULT / REPORT
# ─────────────────────────────────────────────
@app.route("/result")
def result():
    if "scores" not in session or not session["scores"]:
        return redirect(url_for("upload"))

    report = build_report(
        name=session.get("name"),
        domain=session.get("domain"),
        questions=session.get("questions", []),
        answers=session.get("answers", []),
        scores=session.get("scores", []),
        feedbacks=session.get("feedbacks", []),
        sentiments=session.get("sentiments", []),
        skills=session.get("skills", [])
    )
    return render_template("result.html", report=report)


# ─────────────────────────────────────────────
# API: GET STUDY PLAN
# ─────────────────────────────────────────────
@app.route("/api/study-plan", methods=["POST"])
def study_plan():
    from utils.question_generator import call_claude
    domain = session.get("domain", "")
    weak = request.get_json().get("weak_areas", [])
    prompt = (
        f"Create a concise 2-week study plan for a {domain} candidate "
        f"who needs to improve in: {', '.join(weak)}. "
        "Format as day-by-day tasks with resources."
    )
    plan = call_claude(prompt, max_tokens=600)
    return jsonify({"plan": plan})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
