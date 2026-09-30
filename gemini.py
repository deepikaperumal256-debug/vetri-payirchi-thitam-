"""All Gemini calls live here. Falls back to a built-in demo generator when no
API key is configured, so the UI can be developed and tested offline."""
import logging
import time
from . import config

log = logging.getLogger("fitbuddy.gemini")
_client = None


def _get_client():
    global _client
    if _client is None and config.GOOGLE_API_KEY:
        from google import genai
        _client = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _client




def _ask(model: str, prompt: str) -> str:
    client = _get_client()
    candidates = [model, config.FLASH_MODEL, "gemini-3.5-flash",
                  "gemini-flash-latest", "gemini-2.5-flash"]
    last_err = None
    for m in dict.fromkeys(candidates):        # unique, keep order
        for attempt in range(2):
            try:
                resp = client.models.generate_content(model=m, contents=prompt)
                return (resp.text or "").strip()
            except Exception as e:
                last_err = e
                log.warning("Model %s attempt %d failed: %s", m, attempt + 1, str(e)[:200])
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    time.sleep(2)              # transient overload: retry same model once
                    continue
                break                          # 404/429/etc: move to next model
    raise last_err


# ---- Workout generation (Gemini Pro) -----------------------------------
def generate_workout_gemini(name, age, weight, goal, intensity) -> str:
    prompt = f"""You are an experienced certified personal trainer.
Create a 7-day workout plan for {name}: age {age}, weight {weight} kg,
goal "{goal}", preferred intensity "{intensity}".

Format strictly as plain text:
Day 1: <focus>
  Warm-up (5-10 min): ...
  Main workout: <exercise> - <sets> x <reps or duration>, rest <seconds>
  Cooldown/Recovery: ...
...through Day 7. Include at least one rest or active-recovery day.
Keep it safe and appropriate for the age. No intro or outro text."""
    if not _get_client():
        return _demo_plan(goal, intensity)
    return _ask(config.PRO_MODEL, prompt)


# ---- Nutrition tip (Gemini Flash) --------------------------------------
def generate_nutrition_tip_with_flash(goal) -> str:
    prompt = (f'Give ONE concise, practical nutrition or recovery tip (max 2 sentences) '
              f'for someone whose fitness goal is "{goal}". No preamble.')
    if not _get_client():
        return "Prioritise protein at every meal (chicken, fish, beans, Greek yogurt) and stay hydrated."
    return _ask(config.FLASH_MODEL, prompt)


# ---- Feedback-based update (Gemini Pro) --------------------------------
def update_workout_plan(original_plan, feedback) -> str:
    prompt = f"""Here is a user's current 7-day workout plan:

{original_plan}

The user's feedback: "{feedback}"

Revise the plan to reflect the feedback. Keep the same Day 1..Day 7 format
and plain-text style. Output only the updated plan."""
    if not _get_client():
        return original_plan + f"\n\n[DEMO MODE] Plan would be revised for: {feedback}"
    return _ask(config.PRO_MODEL, prompt)


# ---- Offline demo ------------------------------------------------------
def _demo_plan(goal, intensity):
    sets = {"low": "2 x 10", "medium": "3 x 12", "high": "4 x 15"}[intensity]
    days = ["Full body strength", "Cardio intervals", "Upper body", "Active recovery / mobility",
            "Lower body", "Core + conditioning", "Rest day"]
    out = [f"[DEMO MODE - set GOOGLE_API_KEY for real AI plans] Goal: {goal}\n"]
    for i, d in enumerate(days, 1):
        out.append(f"Day {i}: {d}\n  Warm-up (5-10 min): light jog, dynamic stretches\n"
                   f"  Main workout: circuit of 5 exercises - {sets}, rest 60s\n"
                   f"  Cooldown/Recovery: stretching, 5 min breathing\n")
    return "\n".join(out)
