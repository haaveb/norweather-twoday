# Norwegian Weather Forecast

## Overview

The script `norweather_twoday.py` fetches weather data via [MET Weather API](https://api.met.no/) for a given Norwegian municipality, and whose lat. and long. coordinates are found in the local catalogue `kommuners_koordinater.csv` - made with data from [Kartverket](https://www.kartverket.no/). Withouth arguments, it will prompt for the name (Norwegian, not case-sensitive) of a municipality (`kommune`). Data is then gathered & analyzed before presenting the forecast as both a visual plot and command-line table showing temperature, precipitation, wind speeds and wind gusts. I've set a max. limit of 48 hrs because past roughly 54 hrs, time intervals would deviate from 1 hr. By default uses a custom colormap, defined in `palette_static.py`, which in turn was assembled in `palette_cold_neutral_warm.py`. Otherwise, e.g. `viridis` might be good.

### Wind Data Visualization

The forecast displays both sustained wind speeds and wind gusts:
- **Sustained wind**: Dashed line (10-minute average)
- **Wind gusts**: Scattered circles (3-second maximum)

## Third-Party Data

### Municipality Coordinates

Coordinate data for Norwegian municipalities (`kommuners_koordinater.csv`) is derived from:
- **Kartverket** (Norwegian Mapping Authority)
- License: [Norwegian License for Open Government Data (NLOD)](https://data.norge.no/nlod/en/2.0/)
- Source: https://www.kartverket.no/

### Weather Data

Weather forecast data is provided by:
- **Norwegian Meteorological Institute (MET.no)**
- License: [Norwegian License for Open Government Data (NLOD) 2.0](https://data.norge.no/nlod/en/2.0)
- Source: https://api.met.no/

**MET.no Terms Compliance:**
- Data is cached locally with 30-minute expiry to reduce API load.
- User-Agent header identifies this application and maintainer.
- If-Modified-Since header used for efficient requests.
- Attribution displayed in plot and CLI output.

**Note**: While the code is public domain, the weather data from MET.no retains its NLOD 2.0 licensing requirements (attribution).

## Acknowledgements

### Colorblind Simulation

Colorblind transformation matrices derived from:
- **Murtagh, F. and Birch, G. (2006)** "Color blindness and its simulation"
- Via Martin Krzywinski, Canada's Michael Smith Genome Sciences Centre  
- Source: https://mk.bcgsc.ca/colorblind/math.mhtml

Used under academic fair use for accessibility research and implementation.

## Usage

### Basic Usage

```bash
python norweather_twoday.py <kommune> [options]
```

### Examples
```bash
# Basic forecast for Oslo (default 48 hours)
python norweather_twoday.py oslo

# 24-hour forecast for Haugesund
python norweather_twoday.py haugesund --hours 24

# Multi-word municipality (use quotes) or unique word
python norweather_twoday.py "indre fosen"
python norweather_twoday.py fosen

# Duplicate municipality names - multiple options:
python norweather_twoday.py "herøy (møre og romsdal)"  # Full specification
python norweather_twoday.py herøy1                     # Shortcut (alphabetical)
python norweather_twoday.py våler2                     # Second entry

# Plot only (no CLI output), Kragerø
python norweather_twoday.py kragerø --onlyplot

# CLI only (no plot window), Hamar
python norweather_twoday.py hamar --noplot

# Test mode with synthetic data
python norweather_twoday.py --test

# Neon dark mode for Oslo
python norweather_twoday.py oslo --neon
```

### Arguments

- `kommune` - Norwegian municipality name (e.g., oslo, kragerø, "indre fosen")
  - For duplicates, specify (fylke): `"herøy (møre og romsdal)"` or shortcuts: `herøy1`, `herøy2`
- `--hours N` - Number of forecast hours (1-48, default: 48)
- `--noplot` - CLI output only, no plot window
- `--onlyplot` - Plot only, suppress CLI output
- `--test` - Use test mode with synthetic data
- `--neon` - Dark mode with neon feel 

## Prerequisites

Python 3.7+

```bash
pip install requests matplotlib numpy tzdata
```

### For editing Custom Colormap 

The included colormap (`palette_static.py`) works without additional dependencies. To regenerate or modify the colormap (from `palette_cold_neutral_warm.py`):

```bash
# Requires system dependencies
pip install scikit-image
```

## Background and process

This project explores Python syntax, API interaction and color decisions for accessibility and general clarity. For the latter, CIELUV and CIELAB color spaces were explored and utilized. For instance, an intuitive colormap for temperatures was assembled - now exported as static data to eliminate heavy dependencies, but the admittedly messy script creating it is included too. 

## Limitations/Notes

Turned away the idea of API geodata collection for this. Instead, a local file (`kommuners_koordinater.csv`) is used as lookup for coordinates.

## Possibilities
- Make longer forecasts possible by adding some filtering logic. Probably straightforward to get this going, but cumbersome to get neat.
- API geodata lookup --> Provide other place name options, expand outside Norway.
- Dynamic choice of variables of interest etc.
- GUI, Web App etc.
- Further exploring accessibility enhancements.

## Sample Output

### Plot Visualization
![Sample plot](sample_plot.png)
![Sample plot 2](sample_plot2.png)

### Command-Line Forecast
![CLI output](sample_cli.png)
*Example: `python norweather_twoday.py oslo`*

## Repository Structure

- `norweather_twoday.py` - Main weather forecast script
- `palette_static.py` - Pre-computed colormap (no external dependencies)
- `palette_cold_neutral_warm.py` - Colormap generator (development tool)
- `kommuners_koordinater.csv` - Norwegian municipality coordinates catalogue
- `sample_data/` - Sample weather data for testing

## Testing

Test mode generates synthetic data, intented to check functionality with a very large temp. range.

Sample weather data is provided for testing the script, in particular the plot grid alignment.

- `--test` - Synthetic data with extreme temperature range

To use the sample data, provide the sample name as the `kommune` argument:
- `python norweather_twoday.py sample1` - Sample with a large temperature range and no precipitation.
- `python norweather_twoday.py sample2` - Sample with a smaller temperature range and some precipitation.

### Notes

- Use quotes for multi-word municipality names: `"indre fosen"`, `"indre østfold"`
- For duplicate municipality names, specify the fylke: `"våler (østfold)"`, or use shortcut `herøy2`
- For ambiguous names, the script will suggest specific alternatives
- Input is not case-sensitive
