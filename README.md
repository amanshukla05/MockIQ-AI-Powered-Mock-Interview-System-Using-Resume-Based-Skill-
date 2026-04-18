# MockIQ — AI Mock Interview System

A full-stack Flask application that conducts dynamic AI-powered mock interviews
tailored to your resume and target domain.

---

## Features

- Resume upload (PDF or TXT) with automatic skill extraction
- 6 domains: Data Analyst, Web Developer, ML Engineer, Backend, DevOps, Product Manager
- AI-generated interview questions customised to your resume (Claude API)
- Real-time answer evaluation with score (1–10) + feedback
- Follow-up questions generated from your actual answers
- Confidence/sentiment detection (Confident / Neutral / Nervous)
- Final performance report with score chart and weak-area study plan

---

## Project Structure

```
ai_interview/
├── app.py                  ← Flask app & routes
├── requirements.txt
├── .env.example
├── utils/
│   ├── __init__.py
│   ├── resume_parser.py    ← PDF/TXT text extraction
│   ├── skill_extractor.py  ← Domain skill matching
│   ├── question_generator.py ← Claude question generation
│   ├── evaluator.py        ← Claude answer scoring
│   ├── sentiment.py        ← Confidence detection
│   └── report.py           ← Report builder
├── templates/
│   ├── base.html
│   ├── index.html          ← Home page
│   ├── upload.html         ← Resume upload + domain selection
│   ├── skills.html         ← Skills preview
│   ├── interview.html      ← Question + answer + evaluation
│   └── result.html         ← Final report + chart
└── static/
    ├── css/style.css
    ├── js/main.js
    └── uploads/            ← Uploaded resumes (auto-created)
```

---

## Quick Start

### 1. Clone / download the project

```bash
cd ai_interview
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your API key

```bash
cp .env.example .env
```

Edit `.env`:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
SECRET_KEY=any-random-string-here
```

> Get your API key at: https://console.anthropic.com

### 5. Run the app

```bash
python app.py
```

Open: **http://localhost:5000**

---

## Using Without an API Key

The app works without an API key using curated fallback questions and
heuristic scoring. To get full AI-powered questions, evaluation, and
follow-ups, set your `ANTHROPIC_API_KEY`.

---

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required for AI features) |
| `SECRET_KEY` | Flask session secret (any random string) |

---

## Deployment (Render.com)

1. Push project to GitHub
2. Go to https://render.com → New Web Service
3. Connect your repo
4. Set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
5. Add environment variables in Render dashboard
6. Deploy

Add gunicorn to requirements:
```
gunicorn>=21.0.0
```

---

## Deployment (PythonAnywhere)

1. Upload project files via Files tab
2. Create a new Web App → Flask → Python 3.11
3. Set source directory to your project folder
4. Set WSGI file to point to `app.py`
5. Add environment variables in the WSGI config
6. Reload the web app

---

## Adding Voice Input (Optional — Phase 3)

Install Whisper:
```bash
pip install openai-whisper
```

Add a route in `app.py`:
```python
@app.route("/transcribe", methods=["POST"])
def transcribe():
    import whisper
    audio = request.files["audio"]
    audio.save("temp_audio.wav")
    model = whisper.load_model("base")
    result = model.transcribe("temp_audio.wav")
    return jsonify({"text": result["text"]})
```

Then add a microphone button in `interview.html` that records audio
and POSTs it to `/transcribe`.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11 + Flask |
| AI | Anthropic Claude API (claude-opus-4-5) |
| PDF parsing | PyPDF2 |
| Frontend | Jinja2 templates + vanilla JS |
| Charts | Chart.js |
| Fonts | Syne + DM Sans (Google Fonts) |
| Deployment | Render / PythonAnywhere |
