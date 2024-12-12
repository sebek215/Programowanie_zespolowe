# pip install fastapi uvicorn jinja2 python-multipart 
# uvicorn main:app --reload

from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import requests
import csv
from pathlib import Path

app = FastAPI()

# Setup templates
templates = Jinja2Templates(directory="templates")

# Replace with your Google API key
GOOGLE_API_KEY = "AIzaSyAboIDReezqT3bAkS8w8nUV6X9IBRCa3K4"
GOOGLE_SOLAR_API_KEY = "AIzaSyA0oYVrlCJUgO5pwlRcTcUeBroVlJhzojk"

# File paths for user database
USER_DB = "users_db.csv"

# Initialize SQLite for devices
conn = sqlite3.connect("devices.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    device_name TEXT NOT NULL,
    energy_usage REAL DEFAULT 0,  -- Energy in kWh
    uptime TEXT DEFAULT '00:00'   -- Uptime in HH:MM format
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
    cursor.execute("""
        SELECT device_name, energy_usage, uptime FROM devices WHERE username = ?
    """, (username,))
    devices = cursor.fetchall()
    return templates.TemplateResponse("home.html", {"request": request, "username": username, "devices": devices})


@app.post("/add_device", response_class=RedirectResponse)
async def add_device(username: str = Form(...), device_name: str = Form(...)):
    cursor.execute("""
        INSERT INTO devices (username, device_name, energy_usage, uptime) 
        VALUES (?, ?, 0, '00:00')
    """, (username, device_name))
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

@app.get("/solar-check", response_class=HTMLResponse)
async def solar_check(request: Request):
    return templates.TemplateResponse("solar_check.html", {"request": request})


@app.post("/get-solar-data", response_class=HTMLResponse)
async def get_solar_data(request: Request, address: str = Form(...)):
    try:
        # Step 1: Get Latitude and Longitude from Address
        endpoint = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {
            'address': address,
            'key': GOOGLE_API_KEY
        }

        # Send request to Google Maps Geocoding API
        response = requests.get(endpoint, params=params)
        geo_response = response.json()

        if not geo_response.get("results"):
            return templates.TemplateResponse(
                "solar_check.html",
                {"request": request, "error": "Invalid address. Please try again."},
            )

        location = geo_response["results"][0]["geometry"]["location"]
        latitude = location["lat"]
        longitude = location["lng"]

        # Step 2: Call Solar API with Latitude and Longitude
        solar_url = (
            f"https://solar.googleapis.com/v1/dataLayers:get?location.latitude={latitude}&location.longitude={longitude}&radiusMeters=100&view=FULL_LAYERS&requiredQuality=HIGH&exactQualityRequired=true&pixelSizeMeters=0.5&key={GOOGLE_SOLAR_API_KEY}"
        )
        solar_response = requests.get(solar_url).json()
        
        if "error" in solar_response:
            return templates.TemplateResponse(
                "solar_check.html",
                {
                    "request": request,
                    "error": f"Solar API Error: {solar_response['error']['message']}",
                },
            )

        # Step 3: Process and Display Solar Data
        geotiff_data = {
            "DSM (Digital Surface Model)": solar_response.get("dsmUrl"),
            "RGB Imagery": solar_response.get("rgbUrl"),
            "Mask": solar_response.get("maskUrl"),
            "Annual Flux": solar_response.get("annualFluxUrl"),
            "Monthly Flux": solar_response.get("monthlyFluxUrl"),
        }
        hourly_shade_urls = solar_response.get("hourlyShadeUrls", [])

        # Append API key to each URL for authentication
        for key, url in geotiff_data.items():
            if url:
                geotiff_data[key] = f"{url}&key={GOOGLE_SOLAR_API_KEY}"

        hourly_shade_data = [
            f"{url}&key={GOOGLE_SOLAR_API_KEY}" for url in hourly_shade_urls
        ]

        # Extract metadata
        imagery_date = solar_response.get("imageryDate", {})
        processed_date = solar_response.get("imageryProcessedDate", {})
        imagery_quality = solar_response.get("imageryQuality", "Unknown")

        metadata = {
            "Imagery Date": f"{imagery_date.get('year', 'N/A')}-{imagery_date.get('month', 'N/A')}-{imagery_date.get('day', 'N/A')}",
            "Processed Date": f"{processed_date.get('year', 'N/A')}-{processed_date.get('month', 'N/A')}-{processed_date.get('day', 'N/A')}",
            "Imagery Quality": imagery_quality,
        }

        # Render data in HTML template
        return templates.TemplateResponse(
            "solar_check.html",
            {
                "request": request,
                "geotiff_data": geotiff_data,
                "hourly_shade_data": hourly_shade_data,
                "metadata": metadata,
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            "solar_check.html",
            {"request": request, "error": f"An error occurred: {str(e)}"},
        )

# Static files for CSS
app.mount("/static", StaticFiles(directory="static"), name="static")