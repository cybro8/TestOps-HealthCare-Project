from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime  # NEW


# ------------------ Auth Schemas ------------------
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# ------------------ User Schemas ------------------
class UserBase(BaseModel):
    username: str
    role: Optional[str] = "user"


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int

    class Config:
        orm_mode = True


# ------------------ Project Schemas ------------------
class ProjectBase(BaseModel):
    name: str
    organization: str
    pat: str
    iteration_path: Optional[str] = None
    area_path: Optional[str] = None
    api_version: str = "7.0"
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectOut(ProjectBase):
    id: int

    class Config:
        orm_mode = True


# ------------------ Project ↔ User Schemas ------------------
class ProjectUserCreate(BaseModel):
    project_id: int
    user_id: int


class ProjectUserOut(ProjectUserCreate):
    id: int

    class Config:
        orm_mode = True


class ProjectUsersUpdate(BaseModel):
    user_ids: List[int]


# ------------------ Project File Schemas ------------------
class ProjectFileBase(BaseModel):
    filename: str
    filepath: str


class ProjectFileOut(ProjectFileBase):
    id: int
    uploaded_at: datetime

    class Config:
        orm_mode = True


# ------------------ Extended Project Schema with Files ------------------
class ProjectWithFiles(ProjectOut):
    files: List[ProjectFileOut] = []
