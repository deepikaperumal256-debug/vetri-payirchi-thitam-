import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .database import init_db
from .routes import router

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title="FitBuddy - AI Fitness Plan Generator", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(ROOT, "static")), name="static")
app.include_router(router)
