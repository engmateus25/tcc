from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from app.routers.chat import router as chat_router
from app.routers.reports import router as reports_router
from app.routers.agent import router as agent_router
from app.routers.alerts import router as alerts_router
from app.tasks.scheduler import start_scheduler_if_enabled

load_dotenv()

DEFAULT_CORS_ORIGINS = [
    "http://localhost:8100",
    "https://localhost:8100",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


def get_cors_origins():
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw:
        return DEFAULT_CORS_ORIGINS
    configured = [o.strip() for o in raw.split(",") if o.strip()]
    return list(dict.fromkeys([*configured, *DEFAULT_CORS_ORIGINS]))

app = FastAPI(title="AquaMonitor AI Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat_router, prefix="/llm", tags=["llm"])
app.include_router(reports_router, prefix="/reports", tags=["reports"])
app.include_router(agent_router, tags=["agent"])
app.include_router(alerts_router, prefix="/alerts", tags=["alerts"])

# Scheduler 
start_scheduler_if_enabled(app)

@app.get("/health")
def health():
    return {"ok": True}
