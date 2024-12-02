# pip install fastapi uvicorn jinja2 python-multipart 
# uvicorn main:app --reload

from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import csv
from pathlib import Path

app = FastAPI()

# Setup templates
templates = Jinja2Templates(directory="templates")

# File paths for user database
USER_DB = "users_db.csv"

# Initialize SQLite for devices
conn = sqlite3.connect("devices.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    device_name TEXT NOT NULL
)
""")
conn.commit()

# Ensure users.csv exists
if not Path(USER_DB).exists():
    with open(USER_DB, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["username", "password"])  # Header row


# Utility function to check users
def user_exists(username, password=None):
    with open(USER_DB, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["username"] == username and (password is None or row["password"] == password):
                return True
    return False


def register_user(username, password):
    with open(USER_DB, "a") as f:
        writer = csv.writer(f)
        writer.writerow([username, password])


# Routes
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=RedirectResponse)
async def login(username: str = Form(...), password: str = Form(...)):
    if user_exists(username, password):
        return RedirectResponse(url=f"/home/{username}", status_code=302)
    return RedirectResponse(url="/?error=Invalid+credentials", status_code=302)


@app.post("/register", response_class=RedirectResponse)
async def register(username: str = Form(...), password: str = Form(...)):
    if user_exists(username):
        return RedirectResponse(url="/?error=User+already+exists", status_code=302)
    register_user(username, password)
    return RedirectResponse(url="/?success=User+registered", status_code=302)


@app.get("/home/{username}", response_class=HTMLResponse)
async def home(request: Request, username: str):
    cursor.execute("SELECT device_name FROM devices WHERE username = ?", (username,))
    devices = cursor.fetchall()
    return templates.TemplateResponse("home.html", {"request": request, "username": username, "devices": devices})


@app.post("/add_device", response_class=RedirectResponse)
async def add_device(username: str = Form(...), device_name: str = Form(...)):
    cursor.execute("INSERT INTO devices (username, device_name) VALUES (?, ?)", (username, device_name))
    conn.commit()
    return RedirectResponse(url=f"/home/{username}", status_code=302)


@app.post("/remove_device", response_class=RedirectResponse)
async def remove_device(username: str = Form(...), device_name: str = Form(...)):
    cursor.execute("DELETE FROM devices WHERE username = ? AND device_name = ?", (username, device_name))
    conn.commit()
    return RedirectResponse(url=f"/home/{username}", status_code=302)

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Static files for CSS
app.mount("/static", StaticFiles(directory="static"), name="static")
