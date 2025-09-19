from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from . import models, schemas, auth as _auth
from .db import SessionLocal, engine, Base
import os

# Ensure tables exist
Base.metadata.create_all(bind=engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI(title="Auth Service")


def get_db():
    db_sess = SessionLocal()
    try:
        yield db_sess
    finally:
        db_sess.close()

# Ensure admin user exists on startup
@app.on_event("startup")
def ensure_admin():
    db_sess = SessionLocal()
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    existing = db_sess.query(models.User).filter(models.User.username == admin_username).first()
    if not existing:
        hashed = _auth.get_password_hash(admin_password)
        admin = models.User(username=admin_username, password_hash=hashed, role="admin")
        db_sess.add(admin)
        db_sess.commit()
    db_sess.close()

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db_sess: Session = Depends(get_db)):
    user = db_sess.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not _auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    token = _auth.create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

def get_current_user(token: str = Depends(oauth2_scheme), db_sess: Session = Depends(get_db)):
    payload = _auth.decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    username = payload.get("sub")
    user = db_sess.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.get("/me", response_model=schemas.UserOut)
def read_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# Admin endpoints
@app.get("/users", response_model=list[schemas.UserOut])
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