from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Production-tuned engine: proper connection pooling for PostgreSQL
# - pool_size: keep 10 live connections ready
# - max_overflow: allow 20 extra connections under burst load
# - pool_pre_ping: test connections before use (avoids "connection closed" errors)
# - pool_recycle: recycle connections every 5 min to avoid stale connections
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy import event
from sqlalchemy.orm import Session
import asyncio

def trigger_broadcast():
    try:
        loop = asyncio.get_running_loop()
        from .ws_manager import manager
        loop.create_task(manager.broadcast({"type": "DB_UPDATE"}))
    except (RuntimeError, ImportError):
        pass

@event.listens_for(SessionLocal, 'after_commit')
def receive_after_commit(session):
    trigger_broadcast()


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
