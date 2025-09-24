## Overview
The script `norweather_twoday.py` fetches weather data via api.met.no for a given Norwegian municipality, and whose lat. and long. coordinates are found in the `norweather_twoday.csv` catalogue. It prompts for the name (Norwegian, not case-sensitive) of a "kommune". Data is then gathered & analyzed, and a plot is presented, along with some details for temperature, precipitation and wind speeds. I've set a max. limit of 48 hrs because past roughly 54 hrs, time intervals would deviate from 1 hr, which complicates plotting decisions slightly. By default uses my custom colormap, assembled in `palette_cold_neutral_warm.py`. Otherwise, e.g. `managua_r` is good.

## Prerequisites
To run the script:

```bash
pip install requests matplotlib numpy scikit-image
```
where the latter is for the custom colormap.

## Background
This short project was made in order to explore data analysis & general syntax in Python. Have done similar things in MATLAB before (file reading/writing, basic maths & logic, (f-)print, plotting) but the languages differ a little. Spent some time constructing a reasonable, intuitive colormap for the plotted temperature line. Furthermore, getting uniform gridlines for the two y-axes took a little while.

## Limitations/Notes
Gave up on some expansions, first and foremost API geodata collection, due to issues with modules and/or access. Thus ended up just organizing longitude and latitude data, from Kartverket, in a local file instead ('kommuners koordinater.csv'). On the other hand, dealing with the weather data API was surpisingly uneventful.

## Possibilities
- Geodata via API --> Provide other place name options and expand outside Norway.
- Dynamic choice of variables of interest etc.
- GUI etc.

## Sample Output
![Sample plot of temperature and precipitation](sample_plot.png)
