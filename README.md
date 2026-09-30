# FitBuddy – AI Fitness Plan Generator (FastAPI + Gemini)

## Setup
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add your GOOGLE_API_KEY (https://aistudio.google.com/apikey)
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000 (API docs: /docs).

Without a `GOOGLE_API_KEY` the app runs in **demo mode** with canned plans, so you can work on the UI offline.

## Routes
| Route | Purpose |
|---|---|
| `GET /` | Input form |
| `POST /generate-workout` | Gemini Pro plan + Gemini Flash tip, saved to SQLite |
| `GET /plan/{user_id}` | Re-open a saved plan |
| `GET/POST /feedback`, `/submit-feedback` | Regenerate plan from feedback (original kept) |
| `GET /view-all-users` | Admin table (set `ADMIN_TOKEN`, then use `?token=...`) |
| `POST /delete-user/{id}` | Admin delete |

## Structure
```
app/  main.py routes.py gemini.py database.py schemas.py config.py
templates/  base index result feedback all_users
static/  style.css  images/bg.jpg (optional gym background)
```
Models are configurable via `GEMINI_PRO_MODEL` / `GEMINI_FLASH_MODEL` (the spec's Gemini 1.5 models are retired; defaults are 2.5 Pro/Flash).
