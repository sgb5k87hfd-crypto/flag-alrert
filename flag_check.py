import requests
import json
import os
from datetime import datetime, timezone

# ---- CONFIG ----
LAT = 51.2917   # Airdrie, AB - change if you have exact coords
LON = -114.0144
THRESHOLD_KMH = 30
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "CHANGE_ME")
STATE_FILE = "state.json"

# ---- LOAD STATE ----
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        state = json.load(f)
else:
    state = {"flag_up": True, "last_message": None}

# ---- GET WIND DATA ----
url = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    f"&current=wind_speed_10m"
    f"&hourly=wind_speed_10m"
    f"&forecast_days=3"
    f"&wind_speed_unit=kmh"
    f"&timezone=auto"
)
resp = requests.get(url, timeout=15).json()

current_wind = resp["current"]["wind_speed_10m"]
hourly_times = resp["hourly"]["time"]
hourly_winds = resp["hourly"]["wind_speed_10m"]

now_index = 0
for i, t in enumerate(hourly_times):
    if t >= resp["current"]["time"]:
        now_index = i
        break

next_48h = hourly_winds[now_index:now_index + 48]
max_wind_next_48h = max(next_48h) if next_48h else 0
windy_soon = max_wind_next_48h > THRESHOLD_KMH

def notify(message):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": "Flag Alert"},
        timeout=10,
    )
    print("Sent:", message)

today = datetime.now(timezone.utc).date().isoformat()

if state["flag_up"] and current_wind > THRESHOLD_KMH:
    notify(f"Wind is {current_wind:.0f} km/h — take the flag down!")
    state["flag_up"] = False
    state["last_message"] = today

elif not state["flag_up"]:
    if not windy_soon and current_wind <= THRESHOLD_KMH:
        if state.get("last_message") != today:
            notify("Wind has settled and looks calm for 2 days — safe to put the flag back up.")
            state["flag_up"] = True
            state["last_message"] = today
    else:
        if state.get("last_message") != today:
            notify(f"Still windy or more wind coming (up to {max_wind_next_48h:.0f} km/h in next 48h) — leave the flag down for now.")
            state["last_message"] = today

with open(STATE_FILE, "w") as f:
    json.dump(state, f)

print(f"Current wind: {current_wind} km/h | Max next 48h: {max_wind_next_48h} km/h | flag_up={state['flag_up']}")
