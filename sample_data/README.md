# Sample Data

This folder contains sample weather data for testing the plotting functionality.

## Files

- **`sample1.json`** - Hammerfest weather data (Oct 2025)
  - Larger windspeeds range scenario
  - Precipitation axis becomes the "large_axes" with more gridlines
  
## Usage

Use the sample data by specifying it as the kommune argument:

```bash
# Hammerfest sample with large windspeeds range  
python norweather_twoday.py sample1
```

The script automatically recognizes these test inputs and uses the cached data from this folder.