from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, tickets, knowledge_base, telegram
from app.services.email_service import email_listener_loop

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: запускаем фоновое прослушивание почты
    listener_task = asyncio.create_task(email_listener_loop())
    yield
    # Shutdown: останавливаем задачу
    listener_task.cancel()
    
app = FastAPI(
    title="ЭРИС — Служба технической поддержки",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(knowledge_base.router)
app.include_router(telegram.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
