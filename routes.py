import logging
import os
import re
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from . import database as dbm, config
from .gemini import generate_workout_gemini, generate_nutrition_tip_with_flash, update_workout_plan
from .schemas import UserInput, FeedbackRequest

log = logging.getLogger("fitbuddy.routes")
router = APIRouter()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(BASE_DIR), "templates"))


_DAY = re.compile(r"^\s*[#*\s]*(Day\s*\d+)\b[\s:.\-–—*]*(.*)$", re.I)


def split_days(text):
    """Turn 'Day 1: ...' plain text into [{label, focus, body, rest}] for the result page."""
    days, cur, intro = [], None, []
    for line in (text or "").replace("**", "").splitlines():
        m = _DAY.match(line)
        if m:
            cur = {"label": m.group(1).title(), "focus": m.group(2).strip(" :*#"), "body": []}
            days.append(cur)
        elif cur is not None:
            cur["body"].append(line.rstrip())
        else:
            intro.append(line)
    for d in days:
        d["body"] = "\n".join(d["body"]).strip()
        d["rest"] = "rest" in d["focus"].lower()
    return {"days": days, "intro": "\n".join(intro).strip()}


templates.env.filters["split_days"] = split_days


def render(request, name, ctx=None, status_code=200):
    """Compatible with Starlette's TemplateResponse(request, name, context)."""
    return templates.TemplateResponse(request, name, ctx or {}, status_code=status_code)


def get_db():
    db = dbm.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin(request: Request):
    if config.ADMIN_TOKEN and request.query_params.get("token") != config.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin token required (?token=...)")


def _render_result(request, user, plan, message=None, error=None):
    return render(request, "result.html", {
        "user": user, "plan": plan,
        "current_plan": (plan.updated_plan or plan.original_plan) if plan else "",
        "message": message, "error": error,
    })


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return render(request, "index.html", {"error": None})


@router.post("/generate-workout", response_class=HTMLResponse)
def generate_workout(request: Request, username: str = Form(...), user_id: str = Form(...),
                     age: int = Form(...), weight: float = Form(...), goal: str = Form(...),
                     intensity: str = Form(...), db=Depends(get_db)):
    try:
        data = UserInput(username=username.strip(), user_id=user_id.strip(), age=age,
                         weight=weight, goal=goal.strip(), intensity=intensity.lower())
    except ValidationError as e:
        msg = "; ".join(f"{err['loc'][0]}: {err['msg']}" for err in e.errors())
        return render(request, "index.html", {"error": msg}, status_code=422)
    try:
        plan_text = generate_workout_gemini(data.username, data.age, data.weight, data.goal, data.intensity)
        tip = generate_nutrition_tip_with_flash(data.goal)
    except Exception:
        log.exception("Gemini call failed")
        return render(request, "index.html", {"error": "The AI service is unavailable right now. Please try again."},
            status_code=502)
    user = dbm.save_user(db, data)
    dbm.save_plan(db, data.user_id, plan_text, tip)
    return _render_result(request, user, dbm.get_plan(db, data.user_id))


@router.get("/plan/{user_id}", response_class=HTMLResponse)
def view_plan(user_id: str, request: Request, db=Depends(get_db)):
    user, plan = dbm.get_user(db, user_id), dbm.get_plan(db, user_id)
    if not user or not plan:
        raise HTTPException(404, "No plan found for that User ID")
    return _render_result(request, user, plan)


@router.get("/feedback", response_class=HTMLResponse)
def feedback_page(request: Request, user_id: Optional[str] = None):
    return render(request, "feedback.html", {"user_id": user_id or "", "error": None})


@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback(request: Request, user_id: str = Form(...), feedback: str = Form(...),
                    db=Depends(get_db)):
    try:
        data = FeedbackRequest(user_id=user_id.strip(), feedback=feedback.strip())
    except ValidationError:
        return render(request, "feedback.html", {"user_id": user_id,
            "error": "Feedback must be 3-500 characters."}, status_code=422)
    user, plan = dbm.get_user(db, data.user_id), dbm.get_plan(db, data.user_id)
    if not user or not plan:
        return render(request, "feedback.html", {"user_id": data.user_id,
            "error": "No plan found for that User ID. Generate one first."}, status_code=404)
    try:
        new_plan = update_workout_plan(plan.updated_plan or plan.original_plan, data.feedback)
    except Exception:
        log.exception("Gemini update failed")
        return render(request, "feedback.html", {"user_id": data.user_id,
            "error": "The AI service is unavailable right now. Please try again."}, status_code=502)
    dbm.update_plan(db, data.user_id, new_plan, data.feedback)
    return _render_result(request, user, dbm.get_plan(db, data.user_id),
                          message="Your plan has been updated based on your feedback!")


@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(request: Request, db=Depends(get_db), _=Depends(require_admin)):
    return render(request, "all_users.html", {"rows": dbm.get_all_users_with_plans(db),
        "token": request.query_params.get("token", "")})


@router.post("/delete-user/{user_id}")
def delete_user(user_id: str, request: Request, db=Depends(get_db), _=Depends(require_admin)):
    dbm.delete_user(db, user_id)
    token = request.query_params.get("token", "")
    return RedirectResponse(f"/view-all-users{'?token=' + token if token else ''}", status_code=303)
