from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
import os

from . import models, schemas, crud, auth as _auth
from .db import SessionLocal, engine

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="TestOps Project Manager")

# ------------------ Auth Setup ------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Ensure admin user exists on startup
@app.on_event("startup")
def ensure_admin():
    db = SessionLocal()
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    existing = crud.get_user_by_username(db, admin_username)
    if not existing:
        hashed = _auth.get_password_hash(admin_password)
        admin = models.User(username=admin_username, password_hash=hashed, role="admin")
        db.add(admin)
        db.commit()
    db.close()


@app.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, form_data.username)
    if not user or not _auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    token = _auth.create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = _auth.decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    username = payload.get("sub")
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ------------------ Auth Routes ------------------
@app.get("/me", response_model=schemas.UserOut)
def read_me(current_user: models.User = Depends(get_current_user)):
    """Return the current logged-in user's profile"""
    return current_user


# ------------------ User Routes ------------------
@app.post("/users/", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users", response_model=list[schemas.UserOut])
@app.get("/users/", response_model=list[schemas.UserOut])
def list_users(current_user: models.User = Depends(get_current_user), db_sess: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    users = db_sess.query(models.User).all()
    return users

@app.post("/users", response_model=schemas.UserOut)
def create_user(payload: schemas.UserCreate, current_user: models.User = Depends(get_current_user), db_sess: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    existing = db_sess.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = _auth.get_password_hash(payload.password)
    user = models.User(username=payload.username, password_hash=hashed, role=payload.role or "user")
    db_sess.add(user)
    db_sess.commit()
    db_sess.refresh(user)
    return user

@app.put("/users/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, payload: schemas.UserCreate, current_user: models.User = Depends(get_current_user), db_sess: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    user = db_sess.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.username = payload.username or user.username
    if payload.password:
        user.password_hash = _auth.get_password_hash(payload.password)
    user.role = payload.role or user.role
    db_sess.commit()
    db_sess.refresh(user)
    return user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, current_user: models.User = Depends(get_current_user), db_sess: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    user = db_sess.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db_sess.delete(user)
    db_sess.commit()
    return {"detail": "User deleted"}
# ------------------ Project Routes ------------------
@app.post("/projects/", response_model=schemas.ProjectOut)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.create_project(db=db, project=project)


@app.get("/projects/", response_model=List[schemas.ProjectOut])
def list_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_projects(db, skip=skip, limit=limit)


@app.get("/projects/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    success = crud.delete_project(db, project_id=project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"detail": "Project deleted successfully"}


# ------------------ Project ↔ User Routes ------------------
@app.post("/projects/{project_id}/users", response_model=schemas.ProjectUserOut)
def assign_user(project_id: int, project_user: schemas.ProjectUserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if project_user.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")
    return crud.assign_user_to_project(db=db, project_user=project_user)


@app.post("/projects/{project_id}/users/assign", response_model=List[schemas.ProjectUserOut])
def assign_users_batch(
    project_id: int,
    payload: schemas.ProjectUsersUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    print("DEBUG received payload:", payload.dict())  # 👈 add this
    try:
        assigned = crud.update_project_users(
            db=db, project_id=project_id, user_ids=payload.user_ids
        )
        return assigned
    except ValueError as ve:
        print("DEBUG ValueError in assign_users_batch:", ve)  # 👈 add this
        raise HTTPException(status_code=400, detail=str(ve))



@app.get("/projects/{project_id}/users", response_model=List[schemas.ProjectUserOut])
def list_project_users(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_project_users(db=db, project_id=project_id)


@app.delete("/projects/{project_id}/users/{user_id}")
def remove_user(project_id: int, user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    success = crud.remove_user_from_project(db, project_id=project_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not assigned to this project")
    return {"detail": "User removed from project"}
