import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Use DATABASE_URL from environment (set by Railway/Render in production)
# Falls back to local SQLite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mindsense.db")

# PostgreSQL URLs from Railway start with "postgres://" but SQLAlchemy needs "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db_migrations():
    """Idempotently add crisis escalation columns to chat_sessions if missing."""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            if "sqlite" in DATABASE_URL:
                cursor = conn.execute(text("PRAGMA table_info(chat_sessions)"))
                columns = [row[1] for row in cursor.fetchall()]
                if columns:
                    if "crisis_state" not in columns:
                        conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN crisis_state VARCHAR DEFAULT 'no_active_crisis'"))
                    if "escalation_level" not in columns:
                        conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN escalation_level VARCHAR DEFAULT 'none'"))
                    if "last_alert_at" not in columns:
                        conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN last_alert_at DATETIME"))
                    conn.commit()
            else:
                conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS crisis_state VARCHAR DEFAULT 'no_active_crisis'"))
                conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS escalation_level VARCHAR DEFAULT 'none'"))
                conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS last_alert_at TIMESTAMP"))
                conn.commit()
    except Exception as e:
        print(f"[DB MIGRATION WARNING] {e}")

