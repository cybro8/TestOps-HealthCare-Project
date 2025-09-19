from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from .db import Base


# ------------------ User Model ------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String(50), nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    projects = relationship("ProjectUser", back_populates="user")


# ------------------ Project Model ------------------
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)       # Project Name
    organization = Column(String(200), nullable=False)            # Azure DevOps org
    pat = Column(Text, nullable=False)                            # Personal Access Token
    iteration_path = Column(String(300), nullable=True)           # Iteration Path
    area_path = Column(String(300), nullable=True)                # Area Path
    api_version = Column(String(20), default="7.0")               # API Version
    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    users = relationship("ProjectUser", back_populates="project")


# ------------------ Project ↔ User Mapping ------------------
class ProjectUser(Base):
    __tablename__ = "project_users"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    role = Column(String(50), default="member")  # admin / contributor / reader

    project = relationship("Project", back_populates="users")
    user = relationship("User", back_populates="projects")
