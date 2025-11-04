from flask import Flask, jsonify
from flask_cors import CORS
import requests
import datetime
from playwright.sync_api import sync_playwright

app = Flask(__name__)
CORS(app)

# Shared cache variables
cached_weather = None
cached_weather_time = None

cached_course_status = None
cached_course_time = None

cached_notes = None
cached_notes_time = None

@app.route("/")
def home():
    return "✅ Combined scraper app is live."

# ===== WEATHER ROUTES =====
@app.route("/weather")
def fetch_weather():
    global cached_weather, cached_weather_time
    try:
        response = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": 53.455,
            "longitude": -2.384,
            "current_weather": "true",
            "daily": "sunrise,sunset,precipitation_probability_max",
            "timezone": "Europe/London"
        })

        data = response.json()
        current = data["current_weather"]
        daily = data["daily"]

        wind_speed_mph = round(current["windspeed"] * 0.621371, 1)

        cached_weather = {
            "source": "open-meteo.com",
            "temperature": current["temperature"],
            "weather_code": current["weathercode"],
            "wind_speed": wind_speed_mph,
            "precip_chance": daily["precipitation_probability_max"][0],
            "sunrise": daily["sunrise"][0],
            "sunset": daily["sunset"][0]
        }
        cached_weather_time = datetime.datetime.utcnow()
        return jsonify(cached_weather)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/cached-weather")
def get_cached_weather():
    if cached_weather:
        return jsonify(cached_weather)
    return jsonify({"error": "No cached weather available."}), 404

# ===== COURSE STATUS ROUTES =====
@app.route("/course-status")
def scrape_course_status():
    global cached_course_status, cached_course_time
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://davyhulme.intelligentgolf.co.uk/visitorbooking/", timeout=60000)
            page.wait_for_selector(".coursestatus", timeout=15000)

            text = page.locator(".coursestatus").inner_text().strip()

            cached_course_status = {
                "status": text,
                "source": "davyhulme.intelligentgolf.co.uk"
            }
            browser.close()
            return jsonify(cached_course_status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/cached-course")
def get_cached_course_status():
    if cached_course_status:
        return jsonify(cached_course_status)
    return jsonify({"error": "No cached course status available."}), 404

# ===== NOTES ROUTES =====
@app.route("/notes")
def scrape_notes():
    global cached_notes, cached_notes_time
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://davyhulme.intelligentgolf.co.uk/visitorbooking/", timeout=60000)
            page.wait_for_selector(".noteContent", timeout=15000)

            notes = page.locator(".noteContent").all_inner_texts()
            combined_notes = "\n\n".join(notes).strip()

            cached_notes = {
                "note": combined_notes,
                "source": "davyhulme.intelligentgolf.co.uk"
            }
            browser.close()
            return jsonify(cached_notes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/cached-notes")
def get_cached_notes():
    if cached_notes:
        return jsonify(cached_notes)
    return jsonify({"error": "No cached notes available."}), 404
