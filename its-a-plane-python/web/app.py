#!/usr/bin/python3
from flask import Flask, render_template, jsonify, send_from_directory
import json
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# /web is the folder that this file lives in
WEB_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(WEB_DIR, ".."))
SIMULATOR_DIR = os.path.join(WEB_DIR, "static", "simulator")
SIMULATOR_IMAGE = os.path.join(SIMULATOR_DIR, "latest.png")

app = Flask(
    __name__,
    template_folder=os.path.join(WEB_DIR, "templates"),
    static_folder=os.path.join(WEB_DIR, "static")
)

# JSON flight logs (stored outside /web)
CLOSEST_FILE = os.path.join(BASE_DIR, "close.txt")
FARTHEST_FILE = os.path.join(BASE_DIR, "farthest.txt")


def load_json(path, default):
    """Load JSON from a file with proper error handling."""
    if not os.path.exists(path):
        logger.warning(f"File not found: {path}")
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.debug(f"Successfully loaded JSON from {path}")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        return default
    except PermissionError as e:
        logger.error(f"Permission denied reading {path}: {e}")
        return default
    except Exception as e:
        logger.error(f"Could not load {path}: {e}")
        return default


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({"status": "ok"})


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/simulator")
def simulator_page():
    return render_template("simulator.html")


@app.get("/simulator/image")
def simulator_image():
    if not os.path.exists(SIMULATOR_IMAGE):
        logger.warning("Simulator image not found at %s", SIMULATOR_IMAGE)
        return ("Simulator image not found", 404)
    response = send_from_directory(SIMULATOR_DIR, "latest.png")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.get("/closest/json")
def closest_json():
    return jsonify(load_json(CLOSEST_FILE, {}))


@app.get("/farthest/json")
def farthest_json():
    return jsonify(load_json(FARTHEST_FILE, []))


@app.get("/closest")
def closest_page():
    return render_template("closest_map.html")


@app.get("/farthest")
def farthest_page():
    return render_template("farthest_map.html")


# Serve PNG map snapshots from /web/static/maps/
@app.get("/maps/<path:filename>")
def maps(filename):
    maps_dir = os.path.join(WEB_DIR, "static/maps")
    return send_from_directory(maps_dir, filename)


if __name__ == "__main__":
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    logger.info(f"Starting Flask app with debug={debug_mode}")
    app.run(host="0.0.0.0", port=8080, debug=debug_mode)