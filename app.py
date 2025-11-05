from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import datetime
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CACHE_TTL_MINUTES = 5  # Cache expires after 5 minutes
GOLF_COURSE_URL = "https://davyhulme.intelligentgolf.co.uk/visitorbooking/"
WEATHER_LATITUDE = 53.455
WEATHER_LONGITUDE = -2.384

# Cache structure: {data: dict, timestamp: datetime}
cached_weather = None
cached_course_status = None
cached_notes = None


def is_cache_valid(cache_data, ttl_minutes=CACHE_TTL_MINUTES):
    """Check if cached data is still valid based on TTL."""
    if not cache_data or 'timestamp' not in cache_data:
        return False

    elapsed = (datetime.datetime.utcnow() - cache_data['timestamp']).total_seconds()
    return elapsed < (ttl_minutes * 60)


def scrape_golf_course():
    """
    Scrape golf course website for status and notes.
    Returns dict with 'status' and 'notes' keys.
    """
    try:
        logger.info(f"Scraping golf course data from {GOLF_COURSE_URL}")
        response = requests.get(GOLF_COURSE_URL, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract course status
        course_status_elem = soup.select_one('.coursestatus')
        course_status = course_status_elem.get_text(strip=True) if course_status_elem else None

        # Extract notes
        note_elements = soup.select('.noteContent')
        notes = [note.get_text(strip=True) for note in note_elements]
        combined_notes = "\n\n".join(notes) if notes else None

        logger.info(f"Successfully scraped course data (status: {bool(course_status)}, notes: {len(notes)})")

        return {
            'status': course_status,
            'notes': combined_notes,
            'source': 'davyhulme.intelligentgolf.co.uk'
        }

    except requests.RequestException as e:
        logger.error(f"Network error scraping golf course: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error scraping golf course: {e}")
        raise


@app.route("/")
def home():
    return "Combined scraper app is live."


# ===== WEATHER ROUTES =====
@app.route("/weather")
def fetch_weather():
    global cached_weather
    try:
        logger.info("Fetching weather data")
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": WEATHER_LATITUDE,
                "longitude": WEATHER_LONGITUDE,
                "current_weather": "true",
                "daily": "sunrise,sunset,precipitation_probability_max",
                "timezone": "Europe/London"
            },
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        current = data["current_weather"]
        daily = data["daily"]

        wind_speed_mph = round(current["windspeed"] * 0.621371, 1)

        weather_data = {
            "source": "open-meteo.com",
            "temperature": current["temperature"],
            "weather_code": current["weathercode"],
            "wind_speed": wind_speed_mph,
            "precip_chance": daily["precipitation_probability_max"][0],
            "sunrise": daily["sunrise"][0],
            "sunset": daily["sunset"][0]
        }

        cached_weather = {
            'data': weather_data,
            'timestamp': datetime.datetime.utcnow()
        }

        logger.info("Successfully fetched weather data")
        return jsonify(weather_data)

    except requests.RequestException as e:
        logger.error(f"Weather API request failed: {e}")
        return jsonify({"error": "Weather service unavailable"}), 503
    except Exception as e:
        logger.error(f"Unexpected error fetching weather: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/cached-weather")
def get_cached_weather():
    if is_cache_valid(cached_weather):
        age_seconds = (datetime.datetime.utcnow() - cached_weather['timestamp']).total_seconds()
        logger.info(f"Returning cached weather data (age: {age_seconds:.0f}s)")
        return jsonify(cached_weather['data'])

    logger.warning("No valid cached weather available")
    return jsonify({"error": "No cached weather available or cache expired"}), 404


# ===== COURSE STATUS ROUTES =====
@app.route("/course-status")
def scrape_course_status():
    global cached_course_status
    try:
        scraped_data = scrape_golf_course()

        status_data = {
            "status": scraped_data['status'],
            "source": scraped_data['source']
        }

        cached_course_status = {
            'data': status_data,
            'timestamp': datetime.datetime.utcnow()
        }

        return jsonify(status_data)

    except requests.RequestException as e:
        logger.error(f"Failed to scrape course status: {e}")
        return jsonify({"error": "Course website unavailable"}), 503
    except Exception as e:
        logger.error(f"Unexpected error scraping course status: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/cached-course")
def get_cached_course_status():
    if is_cache_valid(cached_course_status):
        age_seconds = (datetime.datetime.utcnow() - cached_course_status['timestamp']).total_seconds()
        logger.info(f"Returning cached course status (age: {age_seconds:.0f}s)")
        return jsonify(cached_course_status['data'])

    logger.warning("No valid cached course status available")
    return jsonify({"error": "No cached course status available or cache expired"}), 404


# ===== NOTES ROUTES =====
@app.route("/notes")
def scrape_notes():
    global cached_notes
    try:
        scraped_data = scrape_golf_course()

        notes_data = {
            "note": scraped_data['notes'],
            "source": scraped_data['source']
        }

        cached_notes = {
            'data': notes_data,
            'timestamp': datetime.datetime.utcnow()
        }

        return jsonify(notes_data)

    except requests.RequestException as e:
        logger.error(f"Failed to scrape notes: {e}")
        return jsonify({"error": "Course website unavailable"}), 503
    except Exception as e:
        logger.error(f"Unexpected error scraping notes: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/cached-notes")
def get_cached_notes():
    if is_cache_valid(cached_notes):
        age_seconds = (datetime.datetime.utcnow() - cached_notes['timestamp']).total_seconds()
        logger.info(f"Returning cached notes (age: {age_seconds:.0f}s)")
        return jsonify(cached_notes['data'])

    logger.warning("No valid cached notes available")
    return jsonify({"error": "No cached notes available or cache expired"}), 404


# ===== COMBINED ROUTE (BONUS) =====
@app.route("/course-info")
def get_combined_course_info():
    """
    Get both course status and notes in a single request.
    More efficient than calling both endpoints separately.
    """
    global cached_course_status, cached_notes

    try:
        scraped_data = scrape_golf_course()

        combined_data = {
            "status": scraped_data['status'],
            "notes": scraped_data['notes'],
            "source": scraped_data['source']
        }

        # Update both caches
        timestamp = datetime.datetime.utcnow()

        cached_course_status = {
            'data': {"status": scraped_data['status'], "source": scraped_data['source']},
            'timestamp': timestamp
        }

        cached_notes = {
            'data': {"note": scraped_data['notes'], "source": scraped_data['source']},
            'timestamp': timestamp
        }

        logger.info("Successfully fetched combined course info")
        return jsonify(combined_data)

    except requests.RequestException as e:
        logger.error(f"Failed to scrape combined course info: {e}")
        return jsonify({"error": "Course website unavailable"}), 503
    except Exception as e:
        logger.error(f"Unexpected error scraping combined course info: {e}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True)
