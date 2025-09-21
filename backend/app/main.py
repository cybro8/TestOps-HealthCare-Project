from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Optional
import os, json ,requests
import shutil
from . import models, schemas, crud, auth as _auth
from .db import SessionLocal, engine, get_db
from requests.auth import HTTPBasicAuth
# Create tables
models.Base.metadata.create_all(bind=engine)
from pydantic import BaseModel
from .models import get_testcase_model
app = FastAPI(title="TestOps Project Manager")
UPLOAD_DIR = "/app/db_data"  # Mounted via docker-compose
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ------------------ Auth Setup ------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")




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
@app.post("/projects", response_model=schemas.ProjectOut)   # <-- use ProjectOut
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = crud.create_project(db=db, project=project)
    crud.create_testcases_table(db_project.id, db)
    return db_project


@app.get("/projects/", response_model=List[schemas.ProjectOut])
def list_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_projects(db, skip=skip, limit=limit)


@app.get("/projects/{project_id}", response_model=schemas.ProjectWithFiles)
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

@app.post("/projects/{project_id}/upload_file", response_model=schemas.ProjectFileOut)
async def upload_file(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    project = crud.get_project(db, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create project-specific directory inside db_data
    project_folder = os.path.join(UPLOAD_DIR, f"project_{project_id}")
    os.makedirs(project_folder, exist_ok=True)

    # Build path and save file
    file_path = os.path.join(project_folder, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Save file metadata in DB
    db_file = models.ProjectFile(
        filename=file.filename,
        filepath=file_path,
        project_id=project_id
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    return db_file


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

@app.get("/users/me/projects", response_model=List[schemas.ProjectOut])
def get_my_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Return only the projects that the logged-in user is assigned to
    return [pu.project for pu in current_user.projects]


@app.get("/projects/{project_id}/testcases")
def get_testcases(project_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    current_user = get_current_user(token, db)

    assigned = db.execute(
        text("SELECT 1 FROM project_users WHERE project_id=:pid AND user_id=:uid"),
        {"pid": project_id, "uid": current_user.id}
    ).fetchone()
    if not assigned:
        raise HTTPException(status_code=403, detail="You are not assigned to this project")

    table_name = f"testcases_project_{project_id}"
    query = text(f"SELECT * FROM {table_name}")
    result = db.execute(query).fetchall()
    return [{"id": r.id, "test_case": r.test_case, "created_at": r.created_at} for r in result]

@app.get("/projects/{project_id}/testcases/{testcase_id}")
def get_testcase(project_id: int, testcase_id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    current_user = get_current_user(token, db)
    assigned = db.execute(
        text("SELECT 1 FROM project_users WHERE project_id=:pid AND user_id=:uid"),
        {"pid": project_id, "uid": current_user.id}
    ).fetchone()
    if not assigned:
        raise HTTPException(status_code=403, detail="You are not assigned to this project")

    table_name = f"testcases_project_{project_id}"
    query = text(f"SELECT * FROM {table_name} WHERE id = :id")
    row = db.execute(query, {"id": testcase_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Test case not found")
    return {"id": row.id, "test_case": row.test_case, "created_at": row.created_at, "updated_at": row.updated_at}


@app.post("/projects/{project_id}/testcases")
def save_testcase(
    project_id: int,
    testcase: dict = Body(...),  # <--- tell FastAPI to parse JSON body
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    current_user = get_current_user(token, db)

    # Check if user is assigned to this project
    assigned = db.execute(
        text("SELECT 1 FROM project_users WHERE project_id=:pid AND user_id=:uid"),
        {"pid": project_id, "uid": current_user.id}
    ).fetchone()

    if not assigned:
        raise HTTPException(status_code=403, detail="You are not assigned to this project")

    # Ensure table exists
    crud.create_testcases_table(project_id, db)

    # Insert the test case JSON
    crud.insert_testcase(project_id, testcase, db)

    return {"status": "success", "message": "Test case saved"}

@app.put("/projects/{project_id}/testcases/{testcase_id}")
def update_testcase(
    project_id: int,
    testcase_id: int,
    testcase: dict = Body(...),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    current_user = get_current_user(token, db)

    assigned = db.execute(
        text("SELECT 1 FROM project_users WHERE project_id=:pid AND user_id=:uid"),
        {"pid": project_id, "uid": current_user.id}
    ).fetchone()
    if not assigned:
        raise HTTPException(status_code=403, detail="You are not assigned to this project")

    table_name = f"testcases_project_{project_id}"
    query = text(f"""
        UPDATE {table_name}
        SET test_case = :test_case, updated_at = now()
        WHERE id = :id
    """)
    db.execute(query, {"test_case": json.dumps(testcase), "id": testcase_id})
    db.commit()
    return {"status": "success", "message": "Test case updated"}


@app.delete("/projects/{project_id}/testcases/{testcase_id}")
def delete_testcase(
    project_id: int,
    testcase_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    current_user = get_current_user(token, db)

    assigned = db.execute(
        text("SELECT 1 FROM project_users WHERE project_id=:pid AND user_id=:uid"),
        {"pid": project_id, "uid": current_user.id}
    ).fetchone()
    if not assigned:
        raise HTTPException(status_code=403, detail="You are not assigned to this project")

    table_name = f"testcases_project_{project_id}"
    query = text(f"DELETE FROM {table_name} WHERE id = :id")
    db.execute(query, {"id": testcase_id})
    db.commit()
    return {"status": "success", "message": "Test case deleted"}


# ----------------- Request Schema -----------------
class DeployRequest(BaseModel):
    project_id: int
    organization: str
    project_name: str
    pat: str
    area_path: Optional[str] = None
    iteration_path: Optional[str] = None

# ----------------- Deploy Endpoint -----------------
@app.post("/deploy_testcases")
def deploy_testcases(req: DeployRequest, db: Session = Depends(get_db)):
    # Get dynamic table model
    TestCase = get_testcase_model(req.project_id)

    try:
        testcases = db.query(TestCase).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch test cases: {str(e)}")

    if not testcases:
        raise HTTPException(status_code=404, detail="No test cases found for this project")

    results = []

    for tc in testcases:
        try:
            tc_data = tc.test_case if isinstance(tc.test_case, dict) else json.loads(tc.test_case)
        except Exception as e:
            print(f"⚠️ Failed to parse test_case ID {tc.id}: {e}")
            tc_data = {}

        test_case_title = tc_data.get("Test Case ID", f"TC_{tc.id}")
        test_case_description = tc_data.get("Description", "")
        test_case_area_path = req.area_path or req.project_name
        test_case_iteration_path = req.iteration_path or f"{req.project_name}\\Sprint 1"

        url = f"https://dev.azure.com/{req.organization}/{req.project_name}/_apis/wit/workitems/$Test%20Case?api-version=7.0"
        payload = [
            {"op": "add", "path": "/fields/System.Title", "value": test_case_title},
            {"op": "add", "path": "/fields/System.Description", "value": test_case_description},
            {"op": "add", "path": "/fields/System.AreaPath", "value": test_case_area_path},
            {"op": "add", "path": "/fields/System.IterationPath", "value": test_case_iteration_path},
        ]
        headers = {"Content-Type": "application/json-patch+json"}

        try:
            response = requests.post(
                url,
                auth=HTTPBasicAuth("", req.pat),
                headers=headers,
                data=json.dumps(payload)
            )
            if response.status_code in (200, 201):
                results.append({"id": test_case_title, "status": "deployed", "detail": "Successfully deployed"})
            else:
                results.append({"id": test_case_title, "status": "failed", "detail": response.text})
        except Exception as e:
            results.append({"id": test_case_title, "status": "failed", "detail": str(e)})

    return {"results": results}