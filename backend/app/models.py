from sqlalchemy import Column, Integer, String, DateTime, Text, func
from .db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String(50), nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


# ------------------ New Table: Project Dashboard ------------------
class ProjectDashboard(Base):
    __tablename__ = "project_dashboards"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(100), nullable=False, unique=True)
    frontend_code = Column(Text, nullable=True)
    backend_code = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
