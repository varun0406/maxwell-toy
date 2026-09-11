from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import settings
from .database import engine, Base
from .routers import auth, parties, invoices, payments, analytics, address_book

# Create tables on startup (Alembic takes over in production)
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Maxwell Mobile Accounting API",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — allow Capacitor app origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:5173",
        "capacitor://localhost",
        "ionic://localhost",
        "https://localhost",
        "https://calculator.rovark.in",
        "http://calculator.rovark.in",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(parties.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(analytics.router)
app.include_router(address_book.router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
