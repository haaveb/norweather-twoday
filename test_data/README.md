# Test Data
This folder contains sample weather data for testing the plotting functionality.

## Files

- **`test1.json`** - Oslo weather data (Sept 2025)
  - Large temperature range scenario
  - Temperature axis becomes the "large_axes" with more gridlines
  
- **`test2.json`** - Tromsø weather data (Sept 2025)  
  - Large precipitation range scenario
  - Precipitation axis becomes the "large_axes" with more gridlines

## Usage
Run the main script and enter "test1" or "test2" as the kommune name:

```bash
python norweather_twoday.py
# Enter: test1   (Oslo - large temperature range)
# Enter: test2   (Tromsø - large precipitation range)
```

The script automatically recognizes these test inputs and uses the cached data from this folder.