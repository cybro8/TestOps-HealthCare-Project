from sqlalchemy.orm import Session
from . import models, schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------ User CRUD ------------------
def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(username=user.username, password_hash=hashed_password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# ------------------ Project CRUD ------------------
def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(
        name=project.name,
        organization=project.organization,
        pat=project.pat,
        iteration_path=project.iteration_path,
        area_path=project.area_path,
        api_version=project.api_version,
        description=project.description,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def get_projects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Project).offset(skip).limit(limit).all()


def delete_project(db: Session, project_id: int):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if project:
        db.delete(project)
        db.commit()
        return True
    return False


# ------------------ Project ↔ User CRUD ------------------
def assign_user_to_project(db: Session, project_user: schemas.ProjectUserCreate):
    db_project_user = models.ProjectUser(
        project_id=project_user.project_id,
        user_id=project_user.user_id,
        role=project_user.role,
    )
    db.add(db_project_user)
    db.commit()
    db.refresh(db_project_user)
    return db_project_user


def get_project_users(db: Session, project_id: int):
    return db.query(models.ProjectUser).filter(models.ProjectUser.project_id == project_id).all()


def remove_user_from_project(db: Session, project_id: int, user_id: int):
    project_user = (
        db.query(models.ProjectUser)
        .filter(models.ProjectUser.project_id == project_id, models.ProjectUser.user_id == user_id)
        .first()
    )
    if project_user:
        db.delete(project_user)
        db.commit()
        return True
    return False
