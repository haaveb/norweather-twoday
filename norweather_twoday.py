# ================================================================================================
# TODAY'S WEATHER FOR A GIVEN NORWEGIAN KOMMUNE
# ================================================================================================
import argparse
import os
import csv
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

# from palette_cold_neutral_warm import get_temperature_colormap
from palette_static import get_colormap

# ================================================================================================
# COMMAND-LINE ARGUMENTS & INPUT HANDLING
# ================================================================================================
print()  # line break for e.g. repeat runs in terminal

parser = argparse.ArgumentParser(
    description='Værvarsel for norsk kommune'
)
parser.add_argument(
    'kommune', nargs='?', help='Navn på norsk kommune (f.eks. oslo eller holmestrand)'
)

# Create mutually exclusive groups for kommune and --test, and for --noplot and --onlyplot
group1 = parser.add_mutually_exclusive_group(required=False)
group1.add_argument(
    '--test', action='store_true', help='Bruk testplot med syntetiske data'
)

group2 = parser.add_mutually_exclusive_group(required=False)
group2.add_argument(
    '--noplot', '--ikkeplot', action='store_true',
    help='Værvarsel til kommandolinje, intet plot'
)
group2.add_argument(
    '--onlyplot', '--kunplot', action='store_true',
    help='Viser plot, ikke kommandilinje-varsel'
)

# Add --hours argument
parser.add_argument(
    '--hours', '--timer', type=int, default=48, metavar='N',
    help='Antall timer for værvarsel (1 til maks. 48)'
)

# Add --neon argument for dark mode
parser.add_argument(
    '--neon', action='store_true', help='Mørk bakgrunn med glød-effekter (neon).'
)

# Parse the arguments
args = parser.parse_args()

# Handle kommune input
if args.test:
    USE_TEST_PLOT = True  # Enable test plot mode
    kommune = "test"  # Internal key (not shown to user)
    display_name = "Test Mode"  # Shown in title / terminal
elif args.kommune:
    kommune = args.kommune.strip().lower()
else:
    kommune = input("Navn på kommune: ").strip().lower()

# Check for conflicting arguments
if args.test and args.kommune:
    parser.error("Kan ikke bruke både --test og kommune samtidig. Vennligst velg én av dem.")

# Validate hours argument
if not 1 <= args.hours <= 48:
    parser.error("Antall timer må være mellom 1 og 48")

# ================================================================================================
# CONFIGURATION CONSTANTS
# ================================================================================================

# Primary Settings (Defaults overridden by args)
FORECAST_HOURS = args.hours
DARK_MODE = args.neon
USE_TEST_PLOT = args.test
SHOW_PLOT = not args.noplot
SHOW_TERMINAL = not args.onlyplot

# Plotting & Style Constants
SHOW_COLORBAR = False
TEST_TEMPERATURE_RANGE = (-40, 40)  
TEST_PRECIP_SCALE = 3.5             # Scale factor for test precipitation to ensure grid alignment

REALLYWARM = 30                     # Attach warmest color to anything >= this constant
TRULYCOLD = -REALLYWARM/2           # Easy solution to make custom palette work

# Glow effect parameters for precipitation line
PRECIP_GLOW_WIDTHS = [10, 4]
PRECIP_GLOW_ALPHAS = [0.08, 0.35]

# Glow effect parameters for wind speed line
WIND_GLOW_WIDTHS = [9, 3.8]
WIND_GLOW_ALPHAS = [0.05, 0.1]

# Glow effect for scatter plots
GLOW_SCATTER_SIZES = [55, 110]      # Large value useful for gust visibility at midnight 
GLOW_SCATTER_ALPHAS = [0.16, 0.08]

# Output mode: by default show BOTH terminal output and plot
if DARK_MODE:
    COLORMAP = get_colormap(dark_mode=True)
    PLOT_COLORS_DM = ("#a95dff", "#45a8e2", "#1d2127", "#465774", "#000000")
    (
        WIND_COLOR, PRECIP_COLOR, 
        BACKGROUND_COLOR, GRIDLINE_COLOR, NEWDAY_COLOR
    ) = PLOT_COLORS_DM
    TEXT_COLOR = "#bfcadf"
else:
    COLORMAP = get_colormap(dark_mode=False)
    PLOT_COLORS_LM = ("#121212", "#1D8E9B", "#9d9d9d", "#505050", "#4e4e4e")
    (
        WIND_COLOR, PRECIP_COLOR, 
        BACKGROUND_COLOR, GRIDLINE_COLOR, NEWDAY_COLOR
    ) = PLOT_COLORS_LM
    TEXT_COLOR = "#121212"

mpl.rcParams['figure.facecolor'] = BACKGROUND_COLOR
mpl.rcParams['axes.facecolor'] = BACKGROUND_COLOR
mpl.rcParams.update({
    'text.color': TEXT_COLOR,'axes.labelcolor': TEXT_COLOR,
    'xtick.color': GRIDLINE_COLOR, 'xtick.labelcolor' : TEXT_COLOR,
    'ytick.color': GRIDLINE_COLOR, 'ytick.labelcolor' : TEXT_COLOR,
    'axes.edgecolor': GRIDLINE_COLOR, 
})

# ================================================================================================
# LOOK UP COORDINATES FOR KOMMUNE
# ================================================================================================
if USE_TEST_PLOT:
    # Skip coordinate lookup in test mode - synthetic data doesn't need real lat/lon
    # Kommune title already set to "Test Plot" in argument parsing section
    pass
else:
    COORDINATES = {
        'sample1': (59.9139, 10.7522),
        'sample2': (69.7444, 18.63)
    }

    def get_coordinates(kommune_name):
        if kommune_name in COORDINATES:
            return COORDINATES[kommune_name], kommune_name.title()
        
        # CSV fallback - skip comment lines starting with #
        # Coordinate data source: Kartverket (Norwegian Mapping Authority)
        with open("kommuners_koordinater.csv", encoding="utf-8") as f:
            # Read lines and filter out comments
            lines = [line for line in f if not line.strip().startswith('#')]
            
            # Create a new string from filtered lines
            from io import StringIO
            csv_content = StringIO(''.join(lines))
            
            # First pass: collect all entries and identify duplicates
            all_entries = []
            duplicate_groups = {}
            
            for row in csv.DictReader(csv_content):
                csv_kommune = row["kommune"].lower()
                fylke = row.get("fylke", "").strip()
                lat, lon = float(row["latitude"]), float(row["longitude"])
                
                all_entries.append((csv_kommune, fylke, lat, lon))
                
                # Group duplicates
                if csv_kommune not in duplicate_groups:
                    duplicate_groups[csv_kommune] = []
                duplicate_groups[csv_kommune].append((fylke, lat, lon))
            
            # Create numbered aliases for duplicates (sorted alphabetically by fylke)
            numbered_aliases = {}
            alias_to_display = {}  # Map aliases to display names
            for kommune_key, entries in duplicate_groups.items():
                if len(entries) > 1:
                    # Sort by fylke alphabetically
                    sorted_entries = sorted(entries, key=lambda x: x[0])
                    for i, (fylke, lat, lon) in enumerate(sorted_entries, 1):
                        alias = f"{kommune_key}{i}"
                        numbered_aliases[alias] = (lat, lon)
                        # Store display name for this alias
                        alias_to_display[alias] = f"{kommune_key.title()} ({fylke})"
    
        # Check numbered aliases
        if kommune_name in numbered_aliases:
            coords = numbered_aliases[kommune_name]
            display_name = alias_to_display[kommune_name]
            return coords, display_name
        
        # Collect ALL matches for ambiguity handling
        exact_matches = []
        
        for csv_kommune, fylke, lat, lon in all_entries:
            # Create full name with fylke if present
            if fylke:
                full_name = f"{csv_kommune} ({fylke.lower()})"
            else:
                full_name = csv_kommune
            
            # Check for exact matches
            if kommune_name == csv_kommune:
                exact_matches.append((csv_kommune, fylke, lat, lon))
            elif kommune_name == full_name:
                display_name = f"{csv_kommune.title()} ({fylke})" if fylke else csv_kommune.title()
                return (lat, lon), display_name

        # Handle exact matches 
        if exact_matches:
            # If only one match and it has no fylke, it's unique
            if len(exact_matches) == 1 and not exact_matches[0][1]:
                match = exact_matches[0]
                return (match[2], match[3]), match[0].title()
            
            # If multiple matches, handle ambiguity
            elif len(exact_matches) > 1:
                # Create helpful error message with all options
                match_descriptions = []
                aliases = []
                sorted_matches = sorted(exact_matches, key=lambda x: x[1] or "")
                
                for i, (kommune, fylke, lat, lon) in enumerate(sorted_matches, 1):
                    if fylke:
                        match_descriptions.append(f"{kommune} ({fylke})")
                        aliases.append(f"{kommune}{i}")
                    else:
                        match_descriptions.append(kommune)
                
                options_text = " or ".join([f"'{desc}'" for desc in match_descriptions])
                if aliases:
                    aliases_text = " or ".join([f"'{alias}'" for alias in aliases])
                    raise ValueError(
                        f"Tvetydig kommune-navn '{kommune_name}'. "
                        f"Flere treff funnet: {', '.join(match_descriptions)}.\n"
                        f"Bruk enten: {options_text}\n"
                        f"Eller snarvei: {aliases_text}"
                    )
                else:
                    raise ValueError(
                        f"Tvetydig kommune-navn '{kommune_name}'. "
                        f"Flere treff funnet: {', '.join(match_descriptions)}. "
                        f"Vennligst spesifiser"
                    )
        
        # If no exact matches found, try partial matching
        partial_matches = []
        
        for csv_kommune, fylke, lat, lon in all_entries:
            # Skip entries that have fylke (duplicates should use exact matching)
            if fylke:
                continue
                
            csv_words = csv_kommune.replace('-', ' ').split()
            input_words = kommune_name.replace('-', ' ').split()
            
            # Check if input matches any word in the CSV entry
            if (kommune_name in csv_words or 
                any(word in csv_words for word in input_words if len(word) > 2)):
                partial_matches.append((csv_kommune, fylke, lat, lon))
        
        # Handle partial matches
        if len(partial_matches) == 1:
            match = partial_matches[0]
            return (match[2], match[3]), match[0].title()
        elif len(partial_matches) > 1:
            match_names = [match[0] for match in partial_matches]
            raise ValueError(
                f"Tvetydig kommune-navn '{kommune_name}'. "
                f"Flere treff funnet: {', '.join(match_names)}. "
                f"Vennligst spesifiser"
            )
        
        # If no matches found at all
        raise ValueError(f"Kommune '{kommune_name}' ikke funnet")

    (latitude, longitude), display_name = get_coordinates(kommune)

# ================================================================================================
# COLLECT & DECIPHER WEATHER DATA
# ================================================================================================

# Initialize data lists (used by both test and normal modes)
times_list = []
temperature_list = []
precipitation_list = []
windspeed_list = []
windgust_list = []

if USE_TEST_PLOT:
    # ---- TEST MODE: GENERATE DATA (W/ LARGE TEMP VARIATION) ------------------------------------
    print(
        f"Using TEST MODE: {TEST_TEMPERATURE_RANGE[0]}°C to "
        f"{TEST_TEMPERATURE_RANGE[1]}°C over {FORECAST_HOURS} hours"
    )
    
    # Generate smooth temperature curve from min to max
    for hour in range(FORECAST_HOURS + 1):
        # Create smooth sinusoidal temperature progression
        progress = hour / FORECAST_HOURS  # 0 to 1
        temp = (
            TEST_TEMPERATURE_RANGE[0] + 
            progress * (TEST_TEMPERATURE_RANGE[1] - TEST_TEMPERATURE_RANGE[0])
        )
        
        # Add some realistic variation
        temp += 3 * np.sin(progress * 4 * np.pi)  # Small oscillations
        
        # Generate time labels
        time_label = f"{hour % 24:02d}.00"
        
        # Generate minimal precipitation/wind for completeness
        # Scale precipitation to ensure good grid alignment with temperature
        # Temp: 80°C range, interval 8 → 11 ticks
        # Want precip: 20mm range, interval 2 → 11 ticks  (20/80 = 1/4 ratio)
        precip = max(
            0, TEST_PRECIP_SCALE * (2 * np.sin(progress * np.pi) + np.random.normal(0, 0.5)))
        windspeed = 5 + 3 * np.sin(progress * 2 * np.pi) + np.random.normal(0, 1)
        # Wind gusts are typically 1.3-1.8x sustained wind speed
        windgust = windspeed * (1.3 + 0.5 * np.random.random()) + np.random.normal(0, 0.5)
        
        times_list.append(time_label)
        temperature_list.append(temp)
        precipitation_list.append(max(0, precip))
        windspeed_list.append(max(0, windspeed))
        windgust_list.append(max(0, windgust))
    
    # Save test data to CSV
    os.makedirs("output", exist_ok=True)
    output_csv_filename = os.path.join("output", "norweather_twoday.csv")
    with open(output_csv_filename, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['time', 'temperature', 'precipitation', 'windspeed', 'windgust'])
        for i in range(len(times_list)):
            csv_writer.writerow([
                times_list[i], 
                temperature_list[i], 
                precipitation_list[i], 
                windspeed_list[i],
                windgust_list[i]
            ])
    # --------------------------------------------------------------------------------------------

else:
    # ---- NORMAL MODE: USE REAL WEATHER DATA ----------------------------------------------------
    os.makedirs("temp_data", exist_ok=True)

    # Check whether cache exists + is recent (from last half hour)
    # Special handling for sample cases
    if kommune in ["sample1", "sample2"]:
        sample_cache_file = os.path.join("sample_data", f"{kommune}.json")
        if os.path.exists(sample_cache_file):
            with open(sample_cache_file, 'r', encoding='utf-8') as cache_file:
                weather_data = json.load(cache_file)
            print(f"Using sample data from {kommune}")
            use_cache = True
        else:
            raise FileNotFoundError(f"Sample data file not found: {sample_cache_file}")
    
    # Normal cache handling
    else:
        cache_dumpfile = os.path.join("temp_data", f"weather_cache_{kommune}.json")
        use_cache = False
        if os.path.exists(cache_dumpfile):
            cache_mtime = os.path.getmtime(cache_dumpfile)
            cache_age_seconds = (datetime.now().timestamp() - cache_mtime)
            if cache_age_seconds < 1800: 
                with open(cache_dumpfile, 'r', encoding='utf-8') as cache_file:
                    weather_data = json.load(cache_file)
                print(
                    f"Using cached weather data for {kommune} "
                    f"(age: {int(cache_age_seconds/60)} min)"
                )
                use_cache = True
    
    # When not using cache
    if not use_cache: 
        url = (
            "https://api.met.no/weatherapi/locationforecast/2.0/complete"
            f"?lat={latitude}&lon={longitude}"
            )
        # Using 'complete' instead of 'compact' above, only because it includes gust speed. 
        headers = {"User-Agent": f"norweather-twoday github.com/haaveb/norweather-twoday"}

        # Add If-Modified-Since if cache exists (even if expired)
        if os.path.exists(cache_dumpfile):
            cache_mtime = os.path.getmtime(cache_dumpfile)
            cache_time = datetime.fromtimestamp(cache_mtime, tz=timezone.utc)
            headers["If-Modified-Since"] = cache_time.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 304:  # Not Modified
            print(f"Server says data unchanged, using existing cache for {kommune}")
            with open(cache_dumpfile, 'r', encoding='utf-8') as cache_file:
                weather_data = json.load(cache_file)
        else:
            weather_data = response.json()
            with open(cache_dumpfile, 'w', encoding='utf-8') as cache_file:
                json.dump(weather_data, cache_file)
            print(f"Fetched and cached new weather data for {kommune}")
    # --------------------------------------------------------------------------------------------

    # ---- UNTANGLE RELEVANT DATA ----------------------------------------------------------------
    weather_timeseries = weather_data["properties"]["timeseries"] # Yields a list of dicts.
    norway_timezone = ZoneInfo("Europe/Oslo")                     # It's Norway time.

    os.makedirs("output", exist_ok=True)
    output_csv_filename = os.path.join("output", "norweather_twoday.csv")
    with open(output_csv_filename, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['time', 'temperature', 'precipitation', 'windspeed', 'windgust'])

        prev_datetime = None
        count = 0
        for hourly_forecast_entry in weather_timeseries:
            if count > FORECAST_HOURS:
                break

            time_string = hourly_forecast_entry["time"]
            datetime_object = datetime.fromisoformat(time_string).astimezone(norway_timezone)

            # Only intervals of 1 hour
            if prev_datetime is None or (datetime_object - prev_datetime).total_seconds() == 3600:
                # Collect
                formatted_time_string = datetime_object.strftime('%H.%M')  # e.g., "10.00"
                instant_weather_details = hourly_forecast_entry["data"]["instant"]["details"]
                temp = instant_weather_details.get("air_temperature")
                windspeed = instant_weather_details.get("wind_speed")
                windgust = instant_weather_details.get("wind_speed_of_gust")
           
                precipitation = (
                    hourly_forecast_entry["data"]
                    .get("next_1_hours", {}).get("details", {}).get("precipitation_amount", 0)
                )

                # Deliver
                data_row = [formatted_time_string, temp, precipitation, windspeed, windgust]
                times_list.append(data_row[0])
                temperature_list.append(data_row[1])
                precipitation_list.append(data_row[2])
                windspeed_list.append(data_row[3])
                windgust_list.append(data_row[4])
                csv_writer.writerow(data_row)

                prev_datetime = datetime_object
                count += 1
            else:
                break  # Stop at first non-hourly interval
    # --------------------------------------------------------------------------------------------

# ================================================================================================
# COMMAND-LINE FORECAST
# ================================================================================================

# ---- ANSI ESCAPE CODES - ONLY USE IF SUPPORTED -------------------------------------------------
def supports_ansi():
    """Check if terminal supports ANSI escape codes"""
    import sys
    
    # Windows Command Prompt (cmd.exe) doesn't support ANSI by default
    if os.name == 'nt':
        # Only enable ANSI on Windows if we're in a modern terminal
        return (
            'ANSICON' in os.environ or           # ConEmu, cmder
            'WT_SESSION' in os.environ or        # Windows Terminal  
            'TERM_PROGRAM' in os.environ or      # VS Code terminal
            'COLORTERM' in os.environ            # Modern terminals
        )
    else:
        # Unix-like systems generally support ANSI
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

# Conditional ANSI code assignment
if supports_ansi():
    BOLD, ITALIC, UNDERLINE, RESET, YELLOW, CYAN = ('\033[1m', '\033[3m', '\033[4m', '\033[0m', '\033[93m', '\033[96m')
else:
    BOLD = ITALIC = UNDERLINE = RESET = YELLOW = CYAN = ''  # Empty strings for CMD

BOX_CHARS = ('┃', '─') if supports_ansi() else ('|', '-')
V_BAR, H_BAR = BOX_CHARS
# ------------------------------------------------------------------------------------------------

if SHOW_TERMINAL:
    if temperature_list and precipitation_list and windspeed_list:
        # Header
        title_name = display_name or kommune.title()
        print(f"{BOLD}Værvarsel for {title_name}, neste {FORECAST_HOURS} timer:{RESET}")
        print()  # Aesthetic line break

        # Sampled time-temperature pairs
        n = len(times_list)
        if n <= 7:
            step = 1
        elif n <= 13:
            step = 2
        elif n <= 19:
            step = 3
        else:
            step = 4
        indices = list(range(0, n, step)) if n > 0 else []
        if indices and indices[-1] != n - 1:
            indices.append(n - 1)

        def format_val(val, width=None):
            """Format value with decimal logic. Optional width for alignment."""
            if val is None or (isinstance(val, float) and np.isnan(val)):
                result = "NA"
            else:
                val = float(val)
                # One decimal place for val < 10, otherwise integer.
                # Reasonable for these ranges, aids readability.
                if abs(val) < 10:
                    result = f"{val:.1f}"
                else:
                    result = f"{int(round(val))}"
            
            # Apply width/alignment if specified
            return f"{result:>{width}}" if width else result

        if indices:
            # Header for the hourly forecast table
            print(f"  {'Tid':^6} {V_BAR} {'Temp.':^7} {V_BAR} {'Vind(kast)':^16} {V_BAR} {'Nedbør':^8}")
            separator = f"  {'':─<6} {V_BAR} {'':─<7} {V_BAR} {'':─<16} {V_BAR} {'':─<8}".replace('─', H_BAR)
            print(separator)
            
            for i in indices:
                t_raw = temperature_list[i]
                p_raw = precipitation_list[i]
                w_raw = windspeed_list[i]
                g_raw = windgust_list[i] if i < len(windgust_list) else None
                time_str = str(times_list[i]).replace('.', ':')
                
                # Format values with proper alignment for CMD compatibility
                t_fmt = f"{format_val(t_raw, 4)} °C"
                p_fmt = f"{format_val(p_raw, 4)} mm"
                
                # Format wind with gust in parentheses
                if g_raw is not None and not (isinstance(g_raw, float) and np.isnan(g_raw)):
                    w_fmt = f"{format_val(w_raw, 3)}  ({format_val(g_raw, 3)}) m/s"
                else:
                    w_fmt = f"{format_val(w_raw, 4)} m/s"
                
                if supports_ansi():
                    # Use colors with exact spacing - account for ANSI codes with wider fields
                    temp_colored = f"{YELLOW}{t_fmt}{RESET}"
                    precip_colored = f"{CYAN}{p_fmt}{RESET}"
                    print(f"  {time_str:<6} {V_BAR} {temp_colored:>15} {V_BAR} {w_fmt:>16} {V_BAR} {precip_colored:>15}")
                else:
                    # CMD-friendly without color codes - use exact widths
                    print(f"  {time_str:<6} {V_BAR} {t_fmt:>7} {V_BAR} {w_fmt:>16} {V_BAR} {p_fmt:>7}")
        else:
            print("  Ingen værvarseldata tilgjengelig.")

        print()  # Aesthetic line break
        print(f"{BOLD}  Oppsummering:{RESET}")
        
        # --- SUMMARY STATS ----------------------------------------------------------------------
        t_avg = np.nanmean(temperature_list)
        p_total = np.nansum(precipitation_list)
        w_max = np.nanmax(windspeed_list)
        
        # Calculate max gust if available
        valid_gusts = [g for g in windgust_list if g is not None and not (isinstance(g, float) and np.isnan(g))]
        g_max = np.nanmax(valid_gusts) if valid_gusts else None
        
        # Separate values and units for formatting
        t_str = format_val(t_avg)
        w_str = format_val(w_max)
        p_str = format_val(p_total)
        
        # Two-column alignment: description & value-with-unit
        label_width = 20  # Width for description column
        
        # Print with two-column alignment - with Windows CMD fallback
        try:
            print(f"{YELLOW}  {'• Snittemperatur:':<{label_width}} {t_str} °C{RESET}")
            print(f"  {'• Maks. middelvind:':<{label_width}} {w_str} m/s")
            if g_max is not None:
                g_str = format_val(g_max)
                print(f"  {'• Maks. vindkast:':<{label_width}} {g_str} m/s")
            print(f"{CYAN}  {'• Total nedbør:':<{label_width}} {p_str} mm{RESET}")

        except UnicodeEncodeError:
            # Fallback for terminals that don't support Unicode bullets
            print(f"{YELLOW}   {'Snittemperatur:':<{label_width-1}} {t_str} °C{RESET}")
            print(f"   {'Maks. middelvind:':<{label_width-1}} {w_str} m/s")
            if g_max is not None:
                g_str = format_val(g_max)
                print(f"   {'Maks. vindkast:':<{label_width-1}} {g_str} m/s")
            print(f"{CYAN}   {'Total nedbør:':<{label_width-1}} {p_str} mm{RESET}")

        print()  # Aesthetic line break
        print("  Værdata: Meteorologisk institutt (MET.no)")
        print()  # Aesthetic line break
        # ----------------------------------------------------------------------------------------
    else:
        print("Ingen data tilgjengelig for kommandolinje værvarsel")
else:
    print("Kun plot, ikke kommandolinje-varsel")

# ================================================================================================
# PLOTTING: (1) GENERAL
# ================================================================================================

#  Dynamic figure sizing based on screen resolution w/ fallback
try:
    # This current setup is overkill but was arduously set up to deal with
    import tkinter as tk
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.destroy()

    # Calculate fig. size conservatively
    fig_width_inches = screen_width / 120
    fig_height_inches = screen_height / 140

    figure, temperature_axes = plt.subplots(figsize=(fig_width_inches, fig_height_inches))
    
except Exception:
    # Fallback to default size
    figure, temperature_axes = plt.subplots(figsize=(10, 6))

figure.suptitle(
    r"$\bf{Temperatur}$, $\bf{Nedbør}$ og $\bf{Vindstyrke}$ - de neste "
    f"{FORECAST_HOURS} timene i {(display_name or kommune.title())}", fontsize=14
)
# Attribution text:
figure.text(0.5, 0.94, "Værdata: Meteorologisk Institutt (MET.no)", 
           ha='center', va='top', fontsize=9, style='italic', alpha=0.8)

time_indices = np.arange(len(times_list))
temperature_values = temperature_list
points_for_segments = np.array([time_indices, temperature_values]).T.reshape(-1, 1, 2)
line_segments = np.concatenate([points_for_segments[:-1], points_for_segments[1:]], axis=1)

# Center colormap at 0 degrees C, distribute (likely unevenly) towards cold and warm ends.
temperature_cmap_norm = TwoSlopeNorm(vmin=TRULYCOLD, vcenter=0, vmax=REALLYWARM)

# Temperature line: segments w/ individual colors
temperature_line_collection = LineCollection(line_segments, 
                                             cmap=COLORMAP,norm=temperature_cmap_norm)
segment_avgs = 0.5 * (np.array(temperature_values[:-1]) + np.array(temperature_values[1:]))
temperature_line_collection.set_array(segment_avgs)
temperature_line_collection.set_linewidth(5.8)
temperature_line_collection.set_capstyle('round')  # Round line ends
temperature_line_collection.set_joinstyle('round') # Round corners
temperature_line_collection.set_zorder(5)  # Ensure temperature line is above vertical lines
temperature_axes.add_collection(temperature_line_collection)
temperature_axes.set_xlim(time_indices.min(), time_indices.max())
temperature_axes.set_ylim(min(temperature_values), max(temperature_values))
temperature_axes.set_ylabel('Temperatur', fontweight='bold', labelpad=12, fontsize=12)

# Set x-ticks with better scaling for different forecast lengths
if FORECAST_HOURS <= 15:
    tick_interval = 1  # Show every hour for short forecasts
elif FORECAST_HOURS <= 30:
    tick_interval = 2  # Every 2 hours for medium forecasts
else:
    tick_interval = 4  # Every 4 hours for long forecasts

xtick_indices = list(range(0, len(times_list), tick_interval))
temperature_axes.set_xticks(xtick_indices)
temperature_axes.set_xticklabels(
    [times_list[i] for i in xtick_indices], 
    rotation=45, ha='right'
)

# Add temperature colorbar if enabled 
if SHOW_COLORBAR:
    colorbar = plt.colorbar(
        temperature_line_collection, ax=temperature_axes, 
        orientation='vertical', pad=0.08, location='left'
    )

# ---- HELPER FUNCTION FOR GLOW EFFECT -------------------------------------------------------
def plot_with_glow(axes, x, y, color, linewidth, glow_linewidths, glow_alphas, **kwargs):
    """Plots a line with a glow effect and returns the main line handle."""
    # Pop zorder to handle it separately and avoid TypeError from **kwargs.
    base_zorder = kwargs.pop('zorder', 1)

    # Plot the glow layers
    for delta_lw, alpha in zip(glow_linewidths, glow_alphas):
        axes.plot(x, y, color=color, linewidth=linewidth + delta_lw, 
                  alpha=alpha, zorder=base_zorder - 0.1, **kwargs)
    
    # Plot the main line on top
    main_line, = axes.plot(x, y, color=color, linewidth=linewidth, 
                           zorder=base_zorder, **kwargs)
    
    return main_line

# ---- PRECIPITATION AND WINDS ---------------------------------------------------------------
# Create a second y-axis for {precipitation, wind speed, wind gusts}
multivar_axes = temperature_axes.twinx()

multivar_axes.set_ylabel(
    'Nedbør (mm)  |  Vindstyrke (m/s)', 
    fontweight='bold', labelpad=20, fontsize=12
)
multivar_axes.tick_params(axis='y')

# Plot precipitation as a blue line
precip_line = plot_with_glow(
    multivar_axes, time_indices, precipitation_list,
    glow_linewidths=PRECIP_GLOW_WIDTHS, glow_alphas=PRECIP_GLOW_ALPHAS,
    label='Nedbør', 
    linewidth=3.5, color=PRECIP_COLOR, zorder=5, solid_capstyle='round'
)

# Fill the area under the precipitation curve
precip_fill = multivar_axes.fill_between(
    time_indices, precipitation_list, color=PRECIP_COLOR, alpha=0.3, zorder=4
)

if DARK_MODE:
    # Plot windspeed as dashed line with glow effect
    wind_line = plot_with_glow(
        multivar_axes, time_indices, windspeed_list, 
        glow_linewidths=WIND_GLOW_WIDTHS, glow_alphas=WIND_GLOW_ALPHAS,
        color=WIND_COLOR,
        linewidth=3.2,
        label='Middelvind',
        linestyle='--',
        zorder=5,
        dash_capstyle='round'
    )
else:
    # Plot windspeed as dashed line without glow
    wind_line, = multivar_axes.plot(
        time_indices, windspeed_list, linestyle='--', 
        linewidth=3.2, label='Middelvind', color=WIND_COLOR, zorder=5, dash_capstyle='round'
        )

wind_line.set_dashes([2, 3])

if DARK_MODE:
    # Plot wind gusts with a glow effect
    base_gust_size = 45
    base_gust_zorder = 6
    # Plot glow layers for scatter
    for size_increase, alpha in zip(GLOW_SCATTER_SIZES, GLOW_SCATTER_ALPHAS):
        multivar_axes.scatter(
            time_indices, windgust_list, s=base_gust_size + size_increase,
            facecolors=WIND_COLOR, edgecolors='none', alpha=alpha, zorder=base_gust_zorder - 0.1
        )
    # Plot main scatter points on top
    gust_scatter = multivar_axes.scatter(
        time_indices, windgust_list, s=base_gust_size,
        label='Vindkast', facecolors=WIND_COLOR, edgecolors='none', zorder=base_gust_zorder
    )
else:
    # Plot wind gusts without glow
    gust_scatter = multivar_axes.scatter(
        time_indices, windgust_list, s=35,
        label='Vindkast', facecolors=WIND_COLOR, edgecolors='none', zorder=6
    )

# --- LEGEND W/ HANDLES --------------------------------------------------------------------------
# Create proxy artist for the temperature line collection, colored from average temperature.
avg_temp = np.nanmean(temperature_values)
avg_temp_color = COLORMAP(temperature_cmap_norm(avg_temp))
temp_legend_line = Line2D(
    [0], [0], color=avg_temp_color, lw=5.5, label='Temperatur'
)

# Define the order and content of the legend
handles = [temp_legend_line, gust_scatter, wind_line, precip_line]
labels = [h.get_label() for h in handles]

# Manually create the legend with the specified order
legend = multivar_axes.legend(
    handles, labels, loc='upper right', framealpha=0.75, handlelength=2.7
)
legend.set_zorder(7)
# ------------------------------------------------------------------------------------------------

# ================================================================================================
# PLOTTING: (2) UNIFORM GRIDLINES AND VISUAL TWEAKS
# ================================================================================================

# ---- GRID ALIGNMENT FOUNDATIONAL LOGIC ---------------------------------------------------------
temperature_min, temperature_max = temperature_axes.get_ylim()
multivar_min, multivar_max = multivar_axes.get_ylim() 

# Visual Preference: Small minimum temperature replaced with zero.
if 0 < temperature_min < 5:
    temperature_min = 0

# Round to whole numbers
temperature_max, temperature_min = np.ceil(temperature_max), np.floor(temperature_min)
multivar_max = np.ceil(multivar_max)
if 0 < multivar_min < 2: # flooring presumed zero values gives -1 
    multivar_min = 0     # ... because of automatic padding, it turns out.
elif multivar_min < 0: 
    multivar_min = 0
else:
    multivar_min = np.floor(multivar_min)

# Ranges for y-axes
temperature_range = temperature_max - temperature_min
multivar_range = multivar_max - multivar_min

# Special handling for test mode to ensure grid alignment
if USE_TEST_PLOT and temperature_range == 80 and abs(multivar_range - 16) < 2:
    # Force precipitation range to 20 to get same number of ticks as temperature
    # Temperature: 80°C, interval 8 → 11 ticks
    # Precipitation: 20mm, interval 2 → 11 ticks (0,2,4,6,8,10,12,14,16,18,20)
    print(f"Test mode: adjusting precip range from {multivar_range:.1f} to 20.0 for grid alignment")
    multivar_max = 20.0
    multivar_range = multivar_max - multivar_min

# Collect data for temperature and multivariate axes
temperature_data = (temperature_min, temperature_max, temperature_range, temperature_axes)
multivar_data = (multivar_min, multivar_max, multivar_range, multivar_axes)

# Determine which data range is smaller and larger
if temperature_range < multivar_range:
    smaller_range_data, larger_range_data = temperature_data, multivar_data
else:
    smaller_range_data, larger_range_data = multivar_data, temperature_data

# Unpack smaller and larger data for further processing
(sm_min, sm_max, sm_range, sm_axes) = smaller_range_data
(lg_min, lg_max, lg_range, lg_axes) = larger_range_data

# Find the smallest integer N, so that N*sm_range >= lg_range
N = int(np.ceil(lg_range / sm_range)) if sm_range > 0 else 1
fitted_lg_range = N * sm_range

# Apply new limits and ticks
lg_axes.set_ylim(lg_min, lg_min + fitted_lg_range)
# ------------------------------------------------------------------------------------------------

# ---- TICKS ADJUSTMENT: DECLUTTER ---------------------------------------------------------------
# Function to determine tick interval based on data range
def get_tick_interval(data_range):
    """Determine appropriate tick interval to avoid cluttered axes"""
    if data_range <= 12:
        return 1
    elif data_range <= 24:
        return 2
    elif data_range <= 48:
        return 4
    else:
        return 8

# Generate tick intervals based on ranges (before any axis scaling)
temperature_tick_interval = get_tick_interval(temperature_range)
multivar_tick_interval = get_tick_interval(multivar_range)

# Apply ticks to both axes
if lg_axes == temperature_axes:
    # Temperature is large axis
    lg_ticks = np.arange(lg_min, lg_min + fitted_lg_range + 1, temperature_tick_interval)
    lg_axes.set_yticks(lg_ticks)
    # Small axis (precipitation) keeps its natural range
    sm_axes.set_ylim(sm_min, sm_max)
    sm_ticks = np.arange(sm_min, sm_max + 1, multivar_tick_interval)
    sm_axes.set_yticks(sm_ticks)
else:
    # Precipitation is large axis
    lg_ticks = np.arange(lg_min, lg_min + fitted_lg_range + 1, multivar_tick_interval)
    lg_axes.set_yticks(lg_ticks)
    # Small axis (temperature) keeps its natural range
    sm_axes.set_ylim(sm_min, sm_max)
    sm_ticks = np.arange(sm_min, sm_max + 1, temperature_tick_interval)
    sm_axes.set_yticks(sm_ticks)

# Add °C suffix to temperature tick labels
temp_formatter = FuncFormatter(lambda y, pos: f'{int(y)}°C')
temperature_axes.yaxis.set_major_formatter(temp_formatter)

# Create a more granular set of ticks for drawing gridlines (every integer)
lg_grid_ticks = np.arange(np.floor(lg_min), np.ceil(lg_min + fitted_lg_range) + 1)

for grid_tick in lg_grid_ticks:
    # Always draw grid lines on temperature_axes (background) to ensure proper layering
    lg_tick = grid_tick # Use grid_tick for calculations
    if lg_axes == temperature_axes:
        # Large axis is temperature - use tick value directly
        draw_y = lg_tick
    else:
        # Large axis is precipitation - convert to temperature coordinate space
        lg_ylim_min, lg_ylim_max = lg_axes.get_ylim()
        temp_ylim_min, temp_ylim_max = temperature_axes.get_ylim()
        # Map from precipitation coordinates to temperature coordinates
        draw_y = (
            temp_ylim_min
            + (lg_tick - lg_ylim_min) * (temp_ylim_max - temp_ylim_min)
            / (lg_ylim_max - lg_ylim_min)
        )
    
    # Convert lg_tick to sm_axes coordinate space for alignment check
    lg_ylim_min, lg_ylim_max = lg_axes.get_ylim()
    sm_ylim_min, sm_ylim_max = sm_axes.get_ylim()
    sm_equiv = (
        sm_ylim_min
        + (lg_tick - lg_ylim_min) * (sm_ylim_max - sm_ylim_min)
        / (lg_ylim_max - lg_ylim_min)
    )
    # Check if any sm_axes tick is close to this equivalent position  
    is_major_aligned = any(abs(sm_tick - sm_equiv) < 0.01 for sm_tick in sm_ticks)
    # Check if the grid tick corresponds to a labeled tick on the large axis
    is_major_unaligned = any(abs(lg_labeled_tick - grid_tick) < 0.01 for lg_labeled_tick in lg_ticks)
    
    # Set 3 layers of y-ticks on larger axis
    if is_major_aligned:
        temperature_axes.axhline(y=draw_y, color=GRIDLINE_COLOR, linewidth=1.65, alpha=0.38, zorder=-1)
    elif is_major_unaligned:
        temperature_axes.axhline(y=draw_y, color=GRIDLINE_COLOR, linewidth=1.3, alpha=0.24, zorder=-1)
    else:
        temperature_axes.axhline(y=draw_y, color=GRIDLINE_COLOR, linewidth=1.3, alpha=0.24, zorder=-1)

# Set up x-axis ticks and grid AFTER y-axis grid alignment
if FORECAST_HOURS <= 15:
    grid_interval = 1    # Every hour
    label_interval = 1   # Show every hour for short forecasts
elif FORECAST_HOURS <= 30:
    grid_interval = 1    # Every hour (denser grid)
    label_interval = 2   # Every 2 hours for medium forecasts
else:
    grid_interval = 2    # Every 2 hours (denser grid)
    label_interval = 4   # Every 4 hours for long forecasts

# Set major ticks for labels (sparse)
xlabel_indices = list(range(0, len(times_list), label_interval))
temperature_axes.set_xticks(xlabel_indices)
temperature_axes.set_xticklabels(
    [times_list[i] for i in xlabel_indices], 
    rotation=45, ha='right'
)

# Set major & minor x-ticks
# Currently same color.
if grid_interval != label_interval:
    xgrid_indices = list(range(0, len(times_list), grid_interval))
    temperature_axes.set_xticks(xgrid_indices, minor=True)
    # Enable both major and minor x-grid WITH DISTINCT STYLES IF DESIRED
    temperature_axes.grid(True, axis='x', which='major',
                          linewidth=1.5, color=GRIDLINE_COLOR, alpha=0.24, zorder=-1)
    temperature_axes.grid(True, axis='x', which='minor', 
                          linewidth=1.5, color=GRIDLINE_COLOR, alpha=0.14, zorder=-1)
else:
    # When intervals are the same, just use major grid
    temperature_axes.grid(True, axis='x', which='major',
                          linewidth=1.5, color=GRIDLINE_COLOR, alpha=0.24, zorder=-1)
# ------------------------------------------------------------------------------------------------

# Add bold vertical line at midnight
for idx, t in enumerate(times_list):
    if t.startswith('00.'):
        y_min, y_max = temperature_axes.get_ylim()
        temperature_axes.plot([idx, idx], [y_min, y_max], 
                              color=NEWDAY_COLOR, linewidth=5.5, alpha=0.65, zorder=2
                              )

plt.tight_layout()

# Simple window maximization
try:
    plt.get_current_fig_manager().window.wm_state('zoomed')
except:
    pass

if SHOW_PLOT:
    plt.show()
else:
    print("Plotting disabled (--noplot).")

# ================================================================================================
# DATA SOURCES & ATTRIBUTION
# ================================================================================================
# Weather data: Norwegian Meteorological Institute (MET.no)
# Municipality coordinates: Kartverket (Norwegian Mapping Authority) - NLOD 2.0 License
# ================================================================================================
