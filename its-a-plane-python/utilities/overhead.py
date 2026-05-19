import os
import logging
import json
import math
import socket
from time import sleep
from threading import Thread, Lock
from datetime import datetime
from typing import Optional, Tuple

import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from urllib3.exceptions import NewConnectionError, MaxRetryError

from config import (
    DISTANCE_UNITS,
    CLOCK_FORMAT,
    MAX_FARTHEST,
    MAX_CLOSEST,
    ADSB_URL,
    RANGE,
    SWIM_API_URL,
    SWIM_API_KEY,
)

from setup import email_alerts
from web import map_generator, upload_helper

# Optional config values

try:
    from config import MIN_ALTITUDE
except (ImportError, ModuleNotFoundError, NameError):
    MIN_ALTITUDE = 0


try:
    from config import ZONE_HOME, LOCATION_HOME
    ZONE_DEFAULT = ZONE_HOME
    LOCATION_DEFAULT = LOCATION_HOME
except (ImportError, ModuleNotFoundError, NameError):
    ZONE_DEFAULT = {"tl_y": 41.904318, "tl_x": -87.647367,
                    "br_y": 41.851654, "br_x": -87.573027}
    LOCATION_DEFAULT = [41.882724, -87.623350]

# Constants

RETRIES = 3
RATE_LIMIT_DELAY = 1
MAX_FLIGHT_LOOKUP = 5
MAX_ALTITUDE = 100000
EARTH_RADIUS_M = 3958.8
BLANK_FIELDS = ["", "N/A", "NONE"]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOG_FILE = os.path.join(BASE_DIR, "close.txt")
LOG_FILE_FARTHEST = os.path.join(BASE_DIR, "farthest.txt")
REFERENCE_DIR = os.path.join(BASE_DIR, "reference")

# --- ADS-B URL formatting ---
# If the URL contains placeholders, format them with home coordinates and range
_ADSB_URL = ADSB_URL
if '{lat}' in _ADSB_URL or '{lon}' in _ADSB_URL or '{range}' in _ADSB_URL:
    _ADSB_URL = _ADSB_URL.format(lat=LOCATION_DEFAULT[0], lon=LOCATION_DEFAULT[1], range=RANGE)

# --- Reference Data Loading ---

def _load_reference(filename):
    """Load a JSON reference file from the reference directory."""
    path = os.path.join(REFERENCE_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.warning("Failed to load reference file %s: %s", filename, e)
        return {}


AIRLINES = _load_reference("airlines.json")
AIRPORTS = _load_reference("airports.json")
REGIONALS = _load_reference("regional.json")

# Build aircraft type lookup with formatted names
_icao_raw = _load_reference("ICAOList.json")
AIRCRAFT_TYPES = {}
for _code, _entry in _icao_raw.items():
    _raw = _entry.get('MANUFACTURER, Model', '') if isinstance(_entry, dict) else ''
    _parts = [p.strip() for p in _raw.split(',', 1)]
    if len(_parts) > 1:
        _name = f"{_parts[0].title()} {_parts[1]}"
    else:
        _name = _raw.title()
    AIRCRAFT_TYPES[_code.upper()] = _name

# Build reverse index: IATA code -> airport entry
AIRPORTS_BY_IATA = {v['iata']: v for v in AIRPORTS.values() if isinstance(v, dict) and v.get('iata')}


def lookup_airport(code):
    """Resolve an airport code (3-char IATA or 4-char ICAO) to its entry."""
    if not code:
        return {}
    if len(code) == 4:
        return AIRPORTS.get(code, {})
    if len(code) == 3:
        return AIRPORTS_BY_IATA.get(code, {})
    return {}


def lookup_airline(icao_code):
    """Resolve an ICAO airline code to its company name with acronym protection."""
    if not icao_code:
        return None
    entry = AIRLINES.get(icao_code.upper())
    if not entry:
        return None
    company = entry.get('Company', '')
    if not company:
        return None
    base_name = company.split(',', 1)[0].strip()
    protected = {'KLM', 'PSA'}
    words = base_name.split()
    formatted_words = [
        word.upper() if word.upper() in protected else word.title()
        for word in words
    ]
    return " ".join(formatted_words)

# Utility Functions

def safe_load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def safe_write_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def ordinal(n: int):
    return f"{n}{'tsnrhtdd'[(n//10 % 10 != 1) * (n % 10 < 4) * n % 10::4]}"


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on Earth.
    
    Uses the Haversine formula to compute the shortest distance over the
    Earth's surface between two points specified by latitude and longitude.
    
    Args:
        lat1: Latitude of the first point in decimal degrees.
        lon1: Longitude of the first point in decimal degrees.
        lat2: Latitude of the second point in decimal degrees.
        lon2: Longitude of the second point in decimal degrees.
    
    Returns:
        The distance between the two points. Units are determined by the
        DISTANCE_UNITS config setting: kilometers if 'metric', miles otherwise.
    """
    lat1, lon1 = map(math.radians, (lat1, lon1))
    lat2, lon2 = map(math.radians, (lat2, lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2)**2 +
        math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    miles = EARTH_RADIUS_M * c

    return miles * 1.609 if DISTANCE_UNITS == "metric" else miles


def degrees_to_cardinal(deg):
    """
    Convert a compass bearing in degrees to a cardinal direction.
    
    Converts a numeric bearing (0-360 degrees) to one of eight cardinal
    or intercardinal directions (N, NE, E, SE, S, SW, W, NW).
    
    Args:
        deg: Compass bearing in degrees (0-360), where 0/360 is North,
             90 is East, 180 is South, and 270 is West.
    
    Returns:
        A string representing the cardinal direction (e.g., 'N', 'NE', 'SW').
    """
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((deg + 22.5) / 45)
    return dirs[idx % 8]


def plane_bearing(lat, lon, home=LOCATION_DEFAULT):
    """
    Calculate the compass bearing from home to a position.
    
    Args:
        lat: Latitude of the aircraft's current position.
        lon: Longitude of the aircraft's current position.
        home: A tuple or list of (latitude, longitude) for the reference
              point. Defaults to LOCATION_DEFAULT.
    
    Returns:
        The bearing in degrees (0-360), where 0 is North, 90 is East,
        180 is South, and 270 is West.
    """
    lat1, lon1 = map(math.radians, home)
    lat2, lon2 = map(math.radians, (lat, lon))

    b = math.atan2(
        math.sin(lon2 - lon1) * math.cos(lat2),
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    )
    return (math.degrees(b) + 360) % 360

# Distance wrappers

def distance_from_home(lat, lon):
    return haversine(lat, lon, LOCATION_DEFAULT[0], LOCATION_DEFAULT[1])


def distance_to_point(lat1, lon1, lat2, lon2):
    return haversine(lat1, lon1, lat2, lon2)

# Logging Closest Flights

def log_flight_data(entry: dict):
    """
    Track and log the top-N closest flights to the home location.
    
    This function maintains a persistent list of the closest flights observed.
    When a new flight enters the top-N closest list, it triggers an email
    notification with an updated map. Existing flights are updated only if
    a closer distance is recorded.
    
    Args:
        entry: A dictionary containing flight data including 'callsign',
               'distance', and other flight details.
    
    Side Effects:
        - Updates the close.txt JSON file with top-N closest flights
        - Sends email alerts for new entries in the top-N list
        - Generates and uploads map visualizations
    """
    try:
        entry["timestamp"] = email_alerts.get_timestamp()
        lst = safe_load_json(LOG_FILE)

        callsigns = {f.get("callsign"): f for f in lst}
        new_call = entry.get("callsign")
        new_dist = entry.get("distance", float("inf"))
        notify = False

        # Existing ? update if better
        if new_call in callsigns:
            idx = next(i for i, f in enumerate(lst) if f.get("callsign") == new_call)
            if new_dist < lst[idx].get("distance", float("inf")):
                lst[idx] = entry
            else:
                return
        else:
            lst.append(entry)

        # Sorting by closest
        lst.sort(key=lambda x: x.get("distance", float("inf")))
        top_n = lst[:MAX_CLOSEST]

        if new_call not in [f["callsign"] for f in top_n]:
            return

        rank = next(i + 1 for i, f in enumerate(top_n) if f["callsign"] == new_call)

        if new_call not in callsigns:
            notify = True

        safe_write_json(LOG_FILE, top_n)

        if notify:
            html = map_generator.generate_closest_map(top_n, filename="closest.html")
            url = upload_helper.upload_map_to_server(html)

            subject = f"New {ordinal(rank)} Closest Flight - {entry.get('callsign','Unknown')}"
            email_alerts.send_flight_summary(subject, entry, map_url=url)

    except Exception as e:
        logging.error("Failed to log closest flight: %s", e)

# Logging Farthest Flights

def log_farthest_flight(entry: dict):
    """
    Track and log flights with the farthest origin or destination airports.
    
    This function maintains a persistent list of flights that have traveled
    from or are traveling to the farthest airports relative to the home
    location. It determines whether the origin or destination is farther
    and records the flight accordingly.
    
    Args:
        entry: A dictionary containing flight data including 'distance_origin',
               'distance_destination', 'origin', 'destination', 'callsign',
               and other flight details.
    
    Side Effects:
        - Updates the farthest.txt JSON file with top-N farthest flights
        - Sends email alerts for new farthest airport entries
        - Generates and uploads map visualizations
    """
    try:
        d_o = entry.get("distance_origin", -1)
        d_d = entry.get("distance_destination", -1)

        if d_o < 0 and d_d < 0:
            return

        reason = "origin" if d_o >= d_d else "destination"
        far = d_o if reason == "origin" else d_d
        airport = entry.get(reason)

        if not airport:
            return

        entry["timestamp"] = email_alerts.get_timestamp()
        entry["reason"] = reason
        entry["farthest_value"] = far
        entry["_airport"] = airport

        lst = safe_load_json(LOG_FILE_FARTHEST)
        airport_map = {f["_airport"]: f for f in lst}

        existing = airport_map.get(airport)
        notify = False
        updated = False

        if existing:
            # Only update if "distance" improved
            if entry["distance"] < existing.get("distance", 9e9):
                lst = [entry if f["_airport"] == airport else f for f in lst]
                updated = True
            else:
                return
        else:
            # New airport entering top-N
            if len(lst) >= MAX_FARTHEST:
                if far <= min(f["farthest_value"] for f in lst):
                    return
            lst.append(entry)
            notify = True
            
        lst.sort(key=lambda x: x["farthest_value"], reverse=True)
        lst = lst[:MAX_FARTHEST]
        safe_write_json(LOG_FILE_FARTHEST, lst)

        # --- ALWAYS generate local map for notify OR updated ---
        if notify or updated:
            html = map_generator.generate_farthest_map(lst, filename="farthest.html")

        # --- ONLY upload + email if this is a NEW airport ---
        if notify:
            url = upload_helper.upload_map_to_server(html)

            rank = next(i for i, f in enumerate(lst) if f["_airport"] == airport) + 1
            cs = entry.get("callsign", "UNKNOWN")

            if rank == 1:
                subject = f"New Farthest Flight ({reason}) - {cs}"
            else:
                subject = f"{ordinal(rank)}-Farthest Flight ({reason}) - {cs}"

            email_alerts.send_flight_summary(subject, entry, reason, map_url=url)

    except Exception as e:
        logging.error("Failed to log farthest flight: %s", e)


# Overhead Class

class Overhead:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
        self._lock = Lock()
        self._data = []
        self._new_data = False
        self._processing = False

    # Public
    def grab_data(self):
        logging.info("Starting new thread to grab flight data.")
        Thread(target=self._grab).start()

    def _get_altitude(self, ac):
        """Returns numeric altitude in feet, or 0 for 'ground' or missing values."""
        alt = ac.get('alt_baro', 0)
        if isinstance(alt, str):
            return 0
        return alt or 0

    def _filter_valid_planes(self, aircraft_list):
        """Filter aircraft to those with required fields, fresh signal, altitude, and within range."""
        # Convert RANGE (nautical miles) to the unit used by haversine
        nm_to_unit = 1.852 if DISTANCE_UNITS == "metric" else 1.15078
        max_distance = RANGE * nm_to_unit

        valid = []
        for ac in aircraft_list:
            if not all(k in ac for k in ('lat', 'lon', 'flight')):
                continue
            if ac.get('seen', 99) >= 15:
                continue
            if self._get_altitude(ac) < MIN_ALTITUDE:
                continue
            dist = distance_from_home(ac['lat'], ac['lon'])
            if dist > max_distance:
                continue
            ac['dist'] = dist
            valid.append(ac)
        return valid

    def _query_swim(self, callsign):
        """Query SWIM API for flight details by callsign. Returns a dict or empty dict."""
        if not SWIM_API_URL or not SWIM_API_KEY:
            return {}
        try:
            response = requests.get(
                f"{SWIM_API_URL}/swim-combined-flights/_search?size=10",
                headers={
                    "Authorization": f"ApiKey {SWIM_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "sort": [{"last_update": {"order": "desc"}}],
                    "query": {
                        "bool": {
                            "filter": [
                                {"term": {"flight_id": callsign}},
                                {"terms": {"latest_status": ["ACTIVE", "PLANNED", "PROPOSED"]}},
                                {"bool": {"must_not": {"range": {"latest_etd": {"gte": "now+6h"}}}}}
                            ]
                        }
                    }
                },
                timeout=5
            )
            response.raise_for_status()
            hits = response.json().get('hits', {}).get('hits', [])
            if not hits:
                return {}

            # Prefer ACTIVE; fall back to most-recently-updated
            active_hits = [h for h in hits if h.get('_source', {}).get('latest_status') == 'ACTIVE']
            best_hit = active_hits[0] if active_hits else hits[0]
            details = best_hit.get('_source', {})

            # Backfill missing fields from other hits on the same leg
            same_leg_hits = [
                h for h in hits
                if h is not best_hit
                and h.get('_source', {}).get('dep_airport') == details.get('dep_airport')
                and h.get('_source', {}).get('arr_airport') == details.get('arr_airport')
            ]
            for h in same_leg_hits:
                for key, val in h.get('_source', {}).items():
                    if val is not None and not details.get(key):
                        details[key] = val

            return details

        except (RequestException, Timeout, ValueError) as e:
            logging.warning("SWIM API query failed for %s: %s", callsign, e)
            return {}

    def _iso_to_unix(self, timestamp_str):
        """Convert an ISO timestamp string to unix epoch seconds, or None."""
        if not timestamp_str:
            return None
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except (ValueError, TypeError):
            return None

    def _build_entry(self, ac, swim_details):
        """Transform ADS-B aircraft + SWIM details into the expected data dict format."""
        callsign = ac.get('flight', '').strip()
        plane_lat = ac['lat']
        plane_lon = ac['lon']

        # Resolve operator/airline — normalize None to empty string
        major_code = swim_details.get('major') or ''
        operator_code = swim_details.get('operator') or ''

        # If major == operator or major == 'XXX', ignore major
        if major_code and (major_code.upper() == operator_code.upper() or major_code.upper() == 'XXX'):
            major_code = ''

        if major_code:
            airline_name = REGIONALS.get(major_code.upper()) or lookup_airline(major_code) or ""
            owner_icao = major_code.upper()
        else:
            airline_name = lookup_airline(operator_code) or ""
            owner_icao = operator_code.upper() if operator_code else ""

        # Aircraft type
        model_val = swim_details.get('aircraft_model') or swim_details.get('aircraft_type') or ''
        plane_code = model_val  # Keep raw code for display (e.g., "B738")

        # Origin/destination airports
        dep_airport_code = swim_details.get('dep_airport', '')
        arr_airport_code = swim_details.get('arr_airport', '')
        
        dep_info = lookup_airport(dep_airport_code)
        arr_info = lookup_airport(arr_airport_code)

        # Get IATA codes for display (scenes expect 3-letter IATA)
        origin_iata = dep_info.get('iata', '') or dep_airport_code or ''
        dest_iata = arr_info.get('iata', '') or arr_airport_code or ''

        # Airport coordinates
        origin_lat = dep_info.get('lat')
        origin_lon = dep_info.get('lon')
        dest_lat = arr_info.get('lat')
        dest_lon = arr_info.get('lon')

        # Distances from plane to airports
        dist_o = distance_to_point(plane_lat, plane_lon, origin_lat, origin_lon) if origin_lat and origin_lon else 0
        dist_d = distance_to_point(plane_lat, plane_lon, dest_lat, dest_lon) if dest_lat and dest_lon else 0

        # Times - convert ISO strings to unix timestamps
        time_sched_dep = self._iso_to_unix(swim_details.get('original_etd') or swim_details.get('latest_etd'))
        time_sched_arr = self._iso_to_unix(swim_details.get('original_eta') or swim_details.get('latest_eta'))
        time_real_dep = self._iso_to_unix(swim_details.get('dep_time_actual') or swim_details.get('dep_time_estimated'))
        time_est_arr = self._iso_to_unix(swim_details.get('latest_eta') or swim_details.get('arr_time_estimated'))

        entry = {
            "airline": airline_name,
            "plane": plane_code,
            "origin": origin_iata,
            "origin_latitude": origin_lat,
            "origin_longitude": origin_lon,
            "destination": dest_iata,
            "destination_latitude": dest_lat,
            "destination_longitude": dest_lon,
            "plane_latitude": plane_lat,
            "plane_longitude": plane_lon,

            "owner_iata": "N/A",
            "owner_icao": owner_icao,

            "time_scheduled_departure": time_sched_dep,
            "time_scheduled_arrival": time_sched_arr,
            "time_real_departure": time_real_dep,
            "time_estimated_arrival": time_est_arr,

            "vertical_speed": ac.get('baro_rate', 0) or 0,
            "callsign": callsign,

            "distance_origin": dist_o,
            "distance_destination": dist_d,
            "distance": ac.get('dist', distance_from_home(plane_lat, plane_lon)),
            "direction": degrees_to_cardinal(plane_bearing(plane_lat, plane_lon)),
        }
        return entry

    def _grab(self):
        with self._lock:
            self._new_data = False
            self._processing = True

        data = []
        swim_cache = {}  # Cache SWIM results by hex code within this cycle

        try:
            logging.info("Fetching aircraft from ADS-B source: %s", _ADSB_URL)
            response = requests.get(_ADSB_URL, timeout=5)
            response.raise_for_status()
            adsb_data = response.json()

            # Handle both adsb.lol format ('ac') and dump1090/tar1090 format ('aircraft')
            aircraft_list = adsb_data.get('ac') or adsb_data.get('aircraft') or []
            logging.info("Received %d aircraft from ADS-B source.", len(aircraft_list))

            # Filter valid planes
            valid_planes = self._filter_valid_planes(aircraft_list)
            logging.info("Filtered to %d valid aircraft.", len(valid_planes))

            if not valid_planes:
                with self._lock:
                    self._new_data = True
                    self._processing = False
                    self._data = data
                return

            # Sort by distance and take top N
            valid_planes.sort(key=lambda ac: ac['dist'])
            closest = valid_planes[:MAX_FLIGHT_LOOKUP]
            logging.info("Processing up to %d closest flights for details.", len(closest))

            for ac in closest:
                callsign = ac.get('flight', '').strip()
                hex_code = ac.get('hex', '').strip().lower()

                if not callsign:
                    continue

                # Check SWIM cache
                if hex_code and hex_code in swim_cache:
                    swim_details = swim_cache[hex_code]
                    logging.info("SWIM cache hit for %s (%s)", callsign, hex_code)
                else:
                    logging.info("Querying SWIM API for %s", callsign)
                    swim_details = self._query_swim(callsign)
                    if hex_code:
                        swim_cache[hex_code] = swim_details

                entry = self._build_entry(ac, swim_details)
                data.append(entry)

                # Log flights
                log_flight_data(entry)
                log_farthest_flight(entry)

                logging.info("Flight processed: %s (dist: %.1f)", callsign, entry['distance'])

            with self._lock:
                self._new_data = True
                self._processing = False
                self._data = data

        except (ConnectionError, NewConnectionError, MaxRetryError, RequestException) as e:
            logging.info("Connection error while fetching flight data: %s", e)
            with self._lock:
                self._new_data = False
                self._processing = False
                
    # Properties
    @property
    def new_data(self):
        with self._lock:
            return self._new_data

    @property
    def processing(self):
        with self._lock:
            return self._processing

    @property
    def data(self):
        with self._lock:
            self._new_data = False
            return list(self._data)

    @property
    def data_is_empty(self):
        return len(self._data) == 0
        
# Main

if __name__ == "__main__":
    o = Overhead()
    o.grab_data()

    while not o.new_data:
        logging.info("processing...")
        sleep(1)

    logging.info(o.data)
