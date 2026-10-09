import os
from sqlmodel import create_engine, Session  # noqa
from msflib.core.config import CoreSettings
from app.core.config import settings

def get_db_url() -> str:
    core_settings: CoreSettings = settings.scope("CORE")
    env_use_sqlite = os.getenv("USE_SQLITE")
    use_sqlite = (
        (env_use_sqlite.lower() in ("true", "1", "yes"))
        if env_use_sqlite is not None
        else getattr(core_settings, "USE_SQLITE", True)
    )

    if use_sqlite:
        return str(core_settings.SQLITE_DATABASE_URI)
    
    db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
        
    return str(core_settings.SQLALCHEMY_DATABASE_URI)


db_url = get_db_url()
if db_url.startswith("sqlite"):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        echo=getattr(settings, "DB_DEBUG_MODE", False),
    )
else:
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        echo=getattr(settings, "DB_DEBUG_MODE", False),
    )

