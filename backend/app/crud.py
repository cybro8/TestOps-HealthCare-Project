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


def assign_user_to_project(db: Session, project_user: schemas.ProjectUserCreate):
    # Ensure the user is not already assigned to another project
    existing = db.query(models.ProjectUser).filter(models.ProjectUser.user_id == project_user.user_id).first()
    if existing:
        raise ValueError(f"User {project_user.user_id} is already assigned to a project")
    db_project_user = models.ProjectUser(
        project_id=project_user.project_id,
        user_id=project_user.user_id,
        role=project_user.role,
    )
    db.add(db_project_user)
    db.commit()
    db.refresh(db_project_user)
    return db_project_user


# Batch update assignments for a project: replace assignments with provided user_ids
def update_project_users(db: Session, project_id: int, user_ids: list[int]):
    # Find users already assigned to other projects
    conflicts = []
    for uid in user_ids:
        q = db.query(models.ProjectUser).filter(models.ProjectUser.user_id == uid).first()
        if q and q.project_id != project_id:
            conflicts.append(uid)
    if conflicts:
        raise ValueError(f"Users already assigned to other projects: {conflicts}")

    # Remove assignments for this project that are not in the new list
    existing = db.query(models.ProjectUser).filter(models.ProjectUser.project_id == project_id).all()
    existing_ids = [e.user_id for e in existing]
    # delete those not in user_ids
    for e in existing:
        if e.user_id not in user_ids:
            db.delete(e)
    # add new assignments
    for uid in user_ids:
        if uid not in existing_ids:
            db_project_user = models.ProjectUser(project_id=project_id, user_id=uid)
            db.add(db_project_user)
    db.commit()
    # return current assignments
    return db.query(models.ProjectUser).filter(models.ProjectUser.project_id == project_id).all()



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
