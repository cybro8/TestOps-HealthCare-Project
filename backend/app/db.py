import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/authdb")

# Connect to DB with retries
engine = None
for i in range(15):
    try:
        engine = create_engine(DATABASE_URL, echo=False, future=True)
        with engine.connect() as conn:
            pass
        print("✅ Database connected")
        break
    except Exception as e:
        print(f"❌ DB connection failed ({i+1}/15): {e}")
        time.sleep(3)

if engine is None:
    raise Exception("Could not connect to the database after retries.")

# Session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Declarative base for models
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
