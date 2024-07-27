from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
import bcrypt
import os

# JWT Configuration
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Database setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "..", "data", "kiosk.db")
TEMPLATES_DIR = os.path.join(BASE_DIR, "..", "web", "templates")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# FastAPI setup
app = FastAPI()
templates = Jinja2Templates(directory=TEMPLATES_DIR)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class KioskNode(Base):
    __tablename__ = "kiosk_nodes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    content = Column(Text)


Base.metadata.create_all(bind=engine)


# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# JWT functions
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")  # Get token from cookies
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if token is None:
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(username=username)
    except JWTError:
        return None
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        return None
    return user


# Helper functions
def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


# Routes
@app.get("/", response_class=HTMLResponse)
async def overview(request: Request, db: Session = Depends(get_db)):
    nodes = db.query(KioskNode).all()
    return templates.TemplateResponse(
        "index.html", {"request": request, "nodes": nodes}
    )


@app.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request, current_user: User = Depends(get_current_user)):
    if current_user:
        # If the user is already authenticated, redirect to the admin dashboard
        return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)

    # Render the login page if not authenticated
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/admin/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        return templates.TemplateResponse(
            "/components/toast-warning.html", {"request": request}
        )
    else:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        response = HTMLResponse(content="", status_code=200)
        response.headers["HX-Redirect"] = "/admin"
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=access_token_expires.total_seconds(),
        )

        return response


@app.post("/admin/logout")
async def logout(request: Request):
    response = HTMLResponse(content="", status_code=200)
    response.headers["HX-Redirect"] = "/"
    response.delete_cookie(key="access_token")  # Clear the JWT cookie
    return response


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    nodes = db.query(KioskNode).all()
    # Set cache control headers to prevent caching
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Cache-Control": "post-check=0, pre-check=0",
        "Pragma": "no-cache",
    }
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "nodes": nodes, "user": current_user},
        headers=headers,
    )


@app.get("/admin/config", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    nodes = db.query(KioskNode).all()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "nodes": nodes, "user": current_user},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
