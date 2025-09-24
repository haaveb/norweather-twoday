### Today's weather for a given norwegian kommune ###
import os
import csv
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import TwoSlopeNorm

from palette_cold_neutral_warm import get_temperature_colormap

# ==== FREQUENTLY ADJUSTED THINGS (& SOME RELATED LOGIC) GROUPED HERE ====
FORECAST_HOURS = 44            # Number of forecast hours, <=48
REALLYWARM = 30 
TRULYCOLD = -REALLYWARM/2
N_COLORS = int(REALLYWARM)*2+1 # Odd number centers white-ish color segment at zero.
COLORMAP, _ = get_temperature_colormap(N_COLORS) # Colormap for temperature line
SHOW_COLORBAR = False

GRIDLINE_COLOR =   "#767A72" # e.g. "#767A72"
BACKGROUND_COLOR = "#ADAAAE" # e.g. "#ADAAAE"
mpl.rcParams['figure.facecolor'] = BACKGROUND_COLOR
mpl.rcParams['axes.facecolor'] = BACKGROUND_COLOR
# =====================================================================

# ==== GET INPUT NAME OF KOMMUNE, LOOK UP COORDINATES IN LOCAL FILE. ====
kommune = input("Navn på kommune: ").strip().lower() # Means 'municipality'.

latitude = longitude = None
with open("kommuners_koordinater.csv", encoding="utf-8") as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for csv_row in csv_reader:
        # Support entries with Saami(?) names sep. by hyphens (ex. "Trondheim - Tråante")
        kommune_names = [part.strip().lower() for part in csv_row["kommune"].split('-')]
        # print(f"Comparing input '{kommune}' with CSV names {kommune_names}")
        if kommune in kommune_names:
            latitude = float(csv_row["latitude"])
            longitude = float(csv_row["longitude"])
            break # When the name is found (and coordinates are collected & set).
if latitude is None:
    raise ValueError(f"Fant ikke kommune '{kommune}' in kommuners_koordinater.csv")
print(f"Coordinates for {kommune.title()}: {latitude}, {longitude}")

# ==== COLLECT AND DECIPHER WEATHER DATA. ====

os.makedirs("temp_data", exist_ok=True)
# Check whether cache exists + is recent (from last half hour)
cache_dumpfile = os.path.join("temp_data", f"weather_cache_{kommune}.json")
use_cache = False
if os.path.exists(cache_dumpfile):
    cache_mtime = os.path.getmtime(cache_dumpfile)
    cache_age_seconds = (datetime.now().timestamp() - cache_mtime)
    if cache_age_seconds < 1800: 
        with open(cache_dumpfile, 'r', encoding='utf-8') as cache_file:
            weather_data = json.load(cache_file)
        print(f"Using cached weather data for {kommune} (age: {int(cache_age_seconds/60)} min)")
        use_cache = True

if not use_cache:
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={latitude}&lon={longitude}"
    headers = {"User-Agent": "BjornHaave/1.0 github.com/haaveb"} # User-Agent required by met.no.
    response = requests.get(url, headers=headers)
    weather_data = response.json()
    # Save only the relevant part (timeseries) and a timestamp
    with open(cache_dumpfile, 'w', encoding='utf-8') as cache_file:
        json.dump(weather_data, cache_file)
    print(f"Fetched and cached new weather data for {kommune}")

# Untangle relevant data.
weather_timeseries = weather_data["properties"]["timeseries"] # Yields a list of dicts.
norway_timezone = ZoneInfo("Europe/Oslo") # It's Norway time.

times_list = [] # Versatile variable in this script.
temperature_list = []
precipitation_list = []
windspeeds_list = []

os.makedirs("output", exist_ok=True)
output_csv_filename = os.path.join("output", "norweather_twoday.csv")
with open(output_csv_filename, 'w', newline='', encoding='utf-8') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['time', 'temperature', 'precipitation', 'windspeed'])

    prev_datetime = None
    count = 0
    for hourly_forecast_entry in weather_timeseries:
        if count > FORECAST_HOURS:
            break

        time_string = hourly_forecast_entry["time"]
        datetime_object = datetime.fromisoformat(time_string).astimezone(norway_timezone)

        # Only intervals of 1 hour.
        if prev_datetime is None or (datetime_object - prev_datetime).total_seconds() == 3600:
            # Collect
            formatted_time_string = datetime_object.strftime('%H.%M')  # e.g., "10.00"
            instant_weather_details = hourly_forecast_entry["data"]["instant"]["details"]
            temp = instant_weather_details.get("air_temperature")
            precipitation = hourly_forecast_entry["data"].get("next_1_hours", {}).get("details", {}).get("precipitation_amount", 0)
            windspeed = instant_weather_details.get("wind_speed")

            # Deliver
            row = [formatted_time_string, temp, precipitation, windspeed]
            times_list.append(row[0])
            temperature_list.append(row[1])
            precipitation_list.append(row[2])
            windspeeds_list.append(row[3])
            csv_writer.writerow(row)

            prev_datetime = datetime_object
            count += 1
        else:
            break  # Stop at first non-hourly interval

# ==== PLOTTING. ====
figure, temperature_axes = plt.subplots(figsize=(10, 6))
figure.suptitle(
    r"$\bf{Temperature}$, $\bf{Precipitation}$ and $\bf{Windspeed}$ - next "
    f"{FORECAST_HOURS} hours in {kommune.title()}", fontsize=14
    )

time_indices = np.arange(len(times_list))
temperature_values = temperature_list
points_for_segments = np.array([time_indices, temperature_values]).T.reshape(-1, 1, 2)
line_segments = np.concatenate([points_for_segments[:-1], points_for_segments[1:]], axis=1)

# Center colormap at 0 degrees C, distribute (likely unevenly) towards cold and warm ends.
temperature_cmap_norm = TwoSlopeNorm(vmin=TRULYCOLD, vcenter=0, vmax=REALLYWARM)

temperature_line_collection = LineCollection(line_segments,
                                             cmap=COLORMAP,norm=temperature_cmap_norm)
segment_avgs = 0.5 * (np.array(temperature_values[:-1]) + np.array(temperature_values[1:]))
temperature_line_collection.set_array(segment_avgs)
temperature_line_collection.set_linewidth(5)
temperature_axes.add_collection(temperature_line_collection)
temperature_axes.set_xlim(time_indices.min(), time_indices.max())
temperature_axes.set_ylim(min(temperature_values), max(temperature_values))
temperature_axes.set_ylabel('Temperature  (°C)', fontweight='bold', labelpad=12)
temperature_axes.grid(True)

# Set x-ticks
if FORECAST_HOURS > 24: 
    tick_interval = 4 # Avoiding x-axis clutter
    xtick_indices = list(range(0, len(times_list), tick_interval))
    temperature_axes.set_xticks(xtick_indices)
    temperature_axes.set_xticklabels(
        [times_list[i] for i in xtick_indices], 
        rotation=45, ha='right'
    )
else:
    temperature_axes.set_xticks(np.arange(len(times_list)))
    temperature_axes.set_xticklabels(times_list, rotation=45, ha='right')

# Add colorbar for temperature if enabled
if SHOW_COLORBAR:
    colorbar = plt.colorbar(
        temperature_line_collection, ax=temperature_axes, 
        orientation='vertical', pad=0.08, location='left'
    )

# Create a second y-axis for precipitation (some space below is good) and windspeed.
precipitation_axes = temperature_axes.twinx()
precipitation_axes.set_ylabel(
    'Precipitation  (mm)   /   Windspeed  (m/s)', 
    fontweight='bold', labelpad=20
)
precipitation_axes.tick_params(axis='y')

# Plot precipitation as a blue line
precipitation_axes.plot(
    time_indices, precipitation_list, label='Precipitation', 
    linewidth=2.5, color='tab:blue'
)

# Plot windspeed as black points
precipitation_axes.scatter(
    time_indices, windspeeds_list, 
    label='Windspeed', color='black', zorder=5
)

# Legend for precipitation and windspeed
precipitation_axes.legend(loc='upper right')

# Add bold vertical lines at the start of each new day (24 hr, midnight).
for idx, t in enumerate(times_list):
    if t.startswith('00.'):
        temperature_axes.axvline(x=idx, color='k', linewidth=2, alpha=0.7, zorder=0)

temperature_axes.grid(linewidth=1.3, color=GRIDLINE_COLOR, alpha=0.5)
precipitation_axes.grid(linewidth=1.3, color=GRIDLINE_COLOR, alpha=0.5)

# ---- UNIFORM GRIDLINES & VISUAL TWEAK ----
temp_min, temp_max = temperature_axes.get_ylim()
precip_min, precip_max = precipitation_axes.get_ylim()

# Visual Preference: small minimum temperature replaced with zero.
if 0 < temp_min < 5:
    temp_min = 0

# Round to whole numbers
temp_min, temp_max = np.floor(temp_min), np.ceil(temp_max)
precip_min = 0 
# Setting to zero avoids added 0 to -1 space introduced by np.floor(precip_min).
# Thus easier to read, and it's always at or near zero anyway.
# Negative precipitation would be cause for alarm.
precip_max = np.ceil(precip_max)

# Ranges for y-axes
temp_range = temp_max - temp_min
precip_range = precip_max - precip_min

if temp_range < precip_range:
    small_min, small_max, small_range = temp_min, temp_max, temp_range
    large_min, large_max, large_range = precip_min, precip_max, precip_range
    small_axes, large_axes = temperature_axes, precipitation_axes
else:
    small_min, small_max, small_range = precip_min, precip_max, precip_range
    large_min, large_max, large_range = temp_min, temp_max, temp_range
    small_axes, large_axes = precipitation_axes, temperature_axes

# Find the smallest integer N, so that N*small_range >= large_range
N = int(np.ceil(large_range / small_range)) if small_range > 0 else 1
new_large_range = N * small_range

# Apply new limits and ticks
large_axes.set_ylim(large_min, large_min + new_large_range)
large_ticks = np.arange(large_min, large_min + new_large_range + 1, 1)
large_axes.set_yticks(large_ticks)
small_axes.set_ylim(small_min, small_max)
small_ticks = np.arange(small_min, small_max + 1, 1)
small_axes.set_yticks(small_ticks)
# ------------------------------------------

plt.tight_layout()
plt.show()
