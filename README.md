# 🔥 SEVIRI Geostationary Fire Detection — Catching What Standard Satellites Miss

> **An open-source Python pipeline for analysing Meteosat SEVIRI fire alerts to quantify fire activity that is systematically missed by polar-orbiting satellites (MODIS/VIIRS) — with district-level spatial attribution and diurnal cycle analysis.**

Developed by [**iForest Global**](https://iforest.global) for monitoring crop residue burning across major agricultural states of India (Punjab, Haryana, Uttar Pradesh, Madhya Pradesh).

---

## 📋 Table of Contents

- [The Problem — Why Standard Satellites Miss Fires](#-the-problem--why-standard-satellites-miss-fires)
- [Why SEVIRI?](#-why-seviri)
- [How This Pipeline Works](#-how-this-pipeline-works)
- [Code Walkthrough](#-code-walkthrough)
- [Satellite Overpass Windows (IST)](#-satellite-overpass-windows-ist)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Configuration](#%EF%B8%8F-configuration)
- [Running the Analysis](#️-running-the-analysis)
- [Outputs](#-outputs)
- [Interpreting the Results](#-interpreting-the-results)
- [Limitations](#️-limitations)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🚨 The Problem — Why Standard Satellites Miss Fires

The two most widely used fire detection satellite systems — **MODIS** (on Terra and Aqua) and **VIIRS** (on Suomi-NPP / NOAA-20) — are mounted on **polar-orbiting, sun-synchronous satellites**. This means they pass over any given location on Earth at the same local time every day.

For India, their overpass windows in **IST (Indian Standard Time)** are:

| Satellite | Platform | Overpass Time (IST) |
|-----------|----------|---------------------|
| MODIS | Terra | ~10:30 |
| MODIS | Aqua | ~13:30 |
| VIIRS | Suomi-NPP | ~13:30 |
| VIIRS | NOAA-20 | ~01:30 (night) |

This creates a fundamental blind spot. **Farmers burning crop residue typically light fires in the early morning (05:00–09:30 IST) and late afternoon/evening (15:30–24:00 IST)** — windows when no polar satellite is overhead.

The result: **official fire count statistics based on MODIS/VIIRS significantly undercount actual fire events.** Reported counts reflect not just how many fires occurred, but *when* they occurred relative to satellite passes.

```
Timeline of a typical stubble burning day (IST):

05:00          10:30         13:30          18:00         22:00
  │              │             │               │             │
  ▼              ▼             ▼               ▼             ▼
Fires start   MODIS Terra   MODIS Aqua     More fires    Night fires
(MISSED ❌)   overpass ✅   overpass ✅    (MISSED ❌)   (MISSED ❌)
```

---

## 🌍 Why SEVIRI?

**SEVIRI** (Spinning Enhanced Visible and InfraRed Imager) is the primary instrument on **Meteosat Second Generation (MSG)** satellites operated by EUMETSAT. Unlike polar orbiting satellites:

| Property | MODIS/VIIRS (Polar) | SEVIRI (Geostationary) |
|----------|--------------------|-----------------------|
| Orbit type | Sun-synchronous LEO | Geostationary |
| Coverage cadence | 1–2 passes/day over India | **Every 15 minutes, 24/7** |
| Spatial resolution | 375 m – 1 km | ~3–4 km at nadir |
| Fire detection | High spatial resolution | **High temporal resolution** |
| Best use | Precise fire location | **Continuous temporal monitoring** |

**SEVIRI's 15-minute repeat cycle** means it can capture fires that start, burn, and extinguish between two MODIS passes — fires that are entirely invisible in the official statistics.

### Data Source

SEVIRI fire alerts are distributed in **CAP (Common Alerting Protocol)** format as `.NAT` binary XML files by **EUMETSAT's Land Surface Analysis Satellite Applications Facility (LSA-SAF)**:

- **Product:** FRM (Fire Radiative Power — MODIS-like) or FD (Fire Detection)
- **Data portal:** [LSA-SAF](https://landsaf.ipma.pt/) / [EUMETSAT EUMETCast](https://www.eumetsat.int/eumetcast)
- **Coverage:** Europe, Africa, Middle East, and **the Indian subcontinent**
- **Cadence:** Every 15 minutes
- **Format:** `.NAT` files (binary-wrapped XML/CAP format)

---

## 🔄 How This Pipeline Works

```
.NAT Files (SEVIRI CAP alerts, 15-min cadence)
              │
              ▼
    ┌─────────────────────┐
    │  Parse .NAT Files   │  → Extract timestamp (UTC→IST) + fire coordinates
    └─────────────────────┘
              │
              ▼
    ┌─────────────────────────────┐
    │  Spatial Join with Districts│  → Assign each fire to State + District
    └─────────────────────────────┘
              │
              ▼
    ┌──────────────────────────────────────┐
    │  Classify by Satellite Window        │
    │  • "Reported" = within MODIS window  │
    │  • "Unreported" = outside window     │
    └──────────────────────────────────────┘
              │
       ┌──────┴──────────────┐
       ▼                     ▼
  Diurnal Analysis     District-level
  (Temporal trends)    Aggregation
       │                     │
       ▼                     ▼
  Charts + Maps         Excel Report
  (PNG, 150–200 dpi)    (3 Sheets)
```

---

## 🧠 Code Walkthrough

The entire pipeline is contained in a single script: **`District_wise_code.py`**

### 1. Configuration Block

```python
DATA_DIR        = r'path/to/NAT_files/'
DATA_DIR_OUTPUT = r'path/to/output/'
FILE_PATTERN    = '*.NAT'
SHAPEFILE_PATH  = r'path/to/District_Boundary.shp'
DIST_COL        = 'District'
STATE_COL       = 'State'
```

Sets all input/output paths and the column names used inside the district shapefile.

---

### 2. State Mapping & Colours

```python
STATE_MAPPING = {'PB': 'Punjab', 'HR': 'Haryana', 'UP': 'Uttar Pradesh', 'MP': 'Madhya Pradesh'}
STATE_COLORS  = {'PB': 'blue', 'HR': 'red', 'UP': 'green', 'MP': 'purple'}
```

Maps two-letter state codes (as they appear in the shapefile) to full names for labelling. Easily extensible to other states.

---

### 3. `is_time_reported(check_time)` — The Core Logic

```python
REPORTED_WINDOWS = [
    (time(0, 30),  time(2, 30)),   # VIIRS night pass window
    (time(10, 30), time(15, 0))    # MODIS Terra + Aqua daytime window
]
```

This function is the analytical heart of the pipeline. Every fire is tested against these windows:

- **Returns `True`** → fire occurred when a polar satellite was likely overhead → **would be counted in standard statistics**
- **Returns `False`** → fire occurred in the blind spot → **missed by MODIS/VIIRS**

The `Unreported (%)` metric in the final report directly quantifies what fraction of each state's fires were invisible to standard monitoring.

---

### 4. `extract_cap_data(filepath)` — NAT File Parser

```python
eff_match = re.search(rb'<effective>(.*?)</effective>', content)
utc_ts    = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
ist_ts    = utc_ts + timedelta(hours=5, minutes=30)   # UTC → IST
matches   = re.findall(r'<circle>([\d\.\-,\s]+)</circle>', xml_content)
```

Each `.NAT` file is a binary file with embedded XML following the **CAP (Common Alerting Protocol)** standard:

- `<effective>` tag → alert timestamp in UTC, converted to IST
- `<circle>` tags → each one is a detected fire point: `lat,lon radius`

The function returns the IST timestamp and a list of `shapely.Point` geometries (one per fire).

---

### 5. Spatial Join — District Attribution

```python
fgdf   = gpd.GeoDataFrame(geometry=fire_pts, crs="EPSG:4326")
joined = gpd.sjoin(fgdf, dist_gdf, how="inner", predicate="within")
```

Each fire point is spatially intersected with the district boundary shapefile using **GeoPandas** `sjoin`. Fires that fall outside all district polygons (e.g., over Pakistan or Nepal) are automatically excluded by the `"inner"` join.

---

### 6. `plot_all_trends(...)` — Diurnal Visualisation

Generates three types of charts:

| Chart | Type | What it shows |
|-------|------|---------------|
| `Trend_Count_{STATE}.png` | Bar chart | Raw fire count per 30-minute slot (per state) |
| `Trend_Perc_{STATE}.png` | Bar chart | % of daily fires per 30-minute slot (per state) |
| `Combined_Trend_Count.png` | Multi-line chart | All states overlaid — raw counts |
| `Combined_Trend_Perc.png` | Multi-line chart | All states overlaid — percentage distribution |

Vertical dashed lines mark the **MODIS Terra (10:30)** and **MODIS Aqua/VIIRS (13:30)** overpass times — making the reporting bias visually obvious.

---

### 7. `add_satellite_annotations(ax)` — Visual Reference Lines

```python
ax.axvline(x=idx, color='black', linestyle='--', alpha=0.6)
ax.text(...)   # Labels: 'MODIS (Terra) 10:30', 'MODIS (Aqua), VIIRS 13:30'
```

Adds annotated vertical lines to every chart at the known overpass times. This makes the charts immediately interpretable for non-technical audiences — you can visually see whether fire peaks align with satellite passes or fall in the blind spot.

---

### 8. Excel Output — Three Sheets

| Sheet | Content |
|-------|---------|
| `Daily_Trend_Report` | One row per 15-min alert file — date, time, fire count per state |
| `Statistical_Summary` | One row per state — total fires, earliest detection, peak hour, unreported % |
| `District_Wise_Report` | One row per fire event — state, district, date, time |

---

## ⏰ Satellite Overpass Windows (IST)

Understanding these windows is essential to interpreting the output:

```
00:00   01:30   02:30   05:00        10:30   13:30        15:00        23:59
  │       │       │       │            │       │            │            │
  │  VIIRS│       │       │      MODIS │  MODIS│            │            │
  │ night │       │       │      Terra │  Aqua │            │            │
  ●───────●───────●───────●────────────●───────●────────────●────────────●
  
  [REPORTED ✅ ]  [   UNREPORTED ❌    ] [R ✅ ] [  UNREPORTED ❌         ]
```

Fires detected by SEVIRI but falling in the **UNREPORTED** zones are the additional fire events this pipeline is designed to quantify and characterise.

---

## 📦 Requirements

### Software

| Tool | Purpose |
|------|---------|
| Python ≥ 3.9 | Core scripting |
| QGIS (optional) | Shapefile inspection / verification |

### Python Libraries

```bash
pip install geopandas pandas numpy matplotlib shapely xlsxwriter
```

### Data Requirements

| Data | Source | Notes |
|------|--------|-------|
| SEVIRI `.NAT` alert files | [LSA-SAF Portal](https://landsaf.ipma.pt/) / EUMETCast | Free registration required |
| District boundary shapefile | [Survey of India](https://onlinemaps.surveyofindia.gov.in/) / State GIS portals | Must have `District` and `State` columns |

---

## 🔧 Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/seviri-fire-detection.git
cd seviri-fire-detection

# Install dependencies
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Open `District_wise_code.py` and edit the configuration block at the top:

```python
# --- REQUIRED: Set your paths ---
DATA_DIR        = r'path/to/your/NAT_files_folder/'
DATA_DIR_OUTPUT = r'path/to/your/output_folder/'
SHAPEFILE_PATH  = r'path/to/District_Boundary.shp'

# --- REQUIRED: Column names in your shapefile ---
DIST_COL  = 'District'   # Column containing district name
STATE_COL = 'State'      # Column containing state code (e.g., 'PB', 'HR')

# --- OPTIONAL: Extend to more states ---
STATE_MAPPING = {
    'PB': 'Punjab',
    'HR': 'Haryana',
    'UP': 'Uttar Pradesh',
    'MP': 'Madhya Pradesh',
    # Add more states here: 'RJ': 'Rajasthan', etc.
}

# --- OPTIONAL: Adjust satellite overpass windows ---
REPORTED_WINDOWS = [
    (time(0, 30), time(2, 30)),    # VIIRS night pass
    (time(10, 30), time(15, 0))    # MODIS day passes
]
```

> ⚠️ **Shapefile column names are case-sensitive.** Run a quick check in Python or QGIS to confirm exact column names before running.

---

## ▶️ Running the Analysis

```bash
python District_wise_code.py
```

Expected console output:

```
Processing 2345 files...
Success! Analysis complete. Files saved in: path/to/output_folder/
```

Runtime depends on the number of `.NAT` files. For a full stubble-burning season (~75 days), expect **3–10 minutes** on a standard laptop.

---

## 📁 Outputs

### Excel Report: `Fire_Analysis_Robust_Report.xlsx`

**Sheet 1 — Daily Trend Report**

| Date | Time | PB_Count | HR_Count | UP_Count | MP_Count |
|------|------|----------|----------|----------|----------|
| 2026-10-15 | 05:30 | 12 | 3 | 0 | 0 |
| 2026-10-15 | 10:45 | 45 | 18 | 7 | 2 |

One row per SEVIRI alert file (15-minute cadence). Use this for custom temporal analysis.

---

**Sheet 2 — Statistical Summary**

| State | Total Fires | Earliest Detection | Peak Fire Hour | Unreported Data (%) |
|-------|-------------|-------------------|----------------|---------------------|
| Punjab | 48,230 | 05:00 | 11:00 | 62.4% |
| Haryana | 19,870 | 05:15 | 10:30 | 58.1% |

The **Unreported Data (%)** column is the key output — it directly answers: *"What fraction of fires in this state would be missed by MODIS/VIIRS-based monitoring?"*

---

**Sheet 3 — District-Wise Report**

| State | District | Date | Time | Fire_Count |
|-------|----------|------|------|------------|
| PB | Amritsar | 2026-10-15 | 05:30 | 3 |
| PB | Ludhiana | 2026-10-15 | 06:00 | 7 |

Granular district-level log of every fire event. Use for identifying hotspot districts and preparing district-wise compliance reports.

---

### Charts

| File | Description |
|------|-------------|
| `Trend_Count_PB.png` | Diurnal fire count bar chart — Punjab |
| `Trend_Count_HR.png` | Diurnal fire count bar chart — Haryana |
| `Trend_Count_UP.png` | Diurnal fire count bar chart — Uttar Pradesh |
| `Trend_Count_MP.png` | Diurnal fire count bar chart — Madhya Pradesh |
| `Trend_Perc_PB.png` | Diurnal % distribution — Punjab |
| `Trend_Perc_HR.png` | Diurnal % distribution — Haryana |
| `Trend_Perc_UP.png` | Diurnal % distribution — Uttar Pradesh |
| `Trend_Perc_MP.png` | Diurnal % distribution — Madhya Pradesh |
| `Combined_Trend_Count.png` | All states — raw counts overlaid |
| `Combined_Trend_Perc.png` | All states — % distribution overlaid |
| `Combined_Spatial_Map.png` | Spatial fire point map coloured by state |

---

## 📊 Interpreting the Results

### Reading the Diurnal Charts

```
Fire Count
   ▲
   │                   ██
   │              ██   ██   ██
   │         ██   ██   ██   ██
   │    ██   ██   ██   ██   ██   ██
   └──────────────────────────────────► Time (IST)
        05   08   10   11   13   16
                  │         │
              MODIS     MODIS Aqua
              Terra     (dashed line)
```

- **Bars to the LEFT of the first dashed line** = fires SEVIRI saw that MODIS Terra did not
- **Bars to the RIGHT of the second dashed line** = fires SEVIRI saw that MODIS Aqua/VIIRS did not
- **Bars between the two dashed lines** = fires likely captured by standard satellites

### The Unreported Percentage

A state with **70% unreported fires** does not mean 70% of fires are hidden — it means 70% of fire *alerts* occurred outside satellite windows. Since SEVIRI detects the same fire multiple times over its burn duration, the true count of unique missed fire *events* requires additional deduplication (see [Limitations](#-limitations)).

### Spatial Map

The `Combined_Spatial_Map.png` shows the geographic distribution of all fire points coloured by state. Dense clusters indicate hotspot sub-districts and help cross-validate district-level results.

---

## ⚠️ Limitations

| Limitation | Detail |
|------------|--------|
| **SEVIRI spatial resolution** | ~3–4 km at the Indian subcontinent (edge of coverage). Small or short-duration fires may be missed. |
| **Fire double-counting** | A single fire burning for 2 hours generates ~8 SEVIRI alerts. The pipeline counts alerts, not unique events. For unique fire counts, spatial-temporal deduplication (clustering within ~5 km, 60 min) is needed. |
| **Cloud contamination** | SEVIRI fire detection is suppressed under heavy cloud cover — especially during pre-monsoon and monsoon periods. |
| **Overpass window approximation** | The `REPORTED_WINDOWS` are approximate. Actual MODIS overpass time varies ±15 minutes by latitude and date. |
| **State code dependency** | The pipeline requires the district shapefile to use the same state abbreviations as `STATE_MAPPING`. Different shapefile sources use different conventions. |

---

## 🤝 Contributing

This tool was built for the Indo-Gangetic Plain stubble burning context, but the methodology is general and applicable to any region with SEVIRI coverage. Contributions welcome:

1. **Fork** the repository
2. Create a feature branch: `git checkout -b feature/deduplication`
3. Open a **Pull Request**

**Suggested extensions:**

- **Spatial-temporal deduplication** — cluster fire points within a radius + time window to estimate unique fire events rather than alert counts
- **Sentinel-3 SLSTR integration** — add a third satellite source for comparison (overpass ~10:00 and ~22:00 IST)
- **Automatic download** — script to pull `.NAT` files from EUMETSAT's data store API
- **Fire Radiative Power (FRP)** — parse FRP values from `.NAT` files to estimate fire intensity, not just count
- **Multi-year trend analysis** — extend to compare stubble burning seasons year-over-year
- **Dashboard** — Streamlit or Dash web UI for interactive exploration of outputs

---

## 📜 License

Released under the **MIT License** — free to use, modify, and distribute with attribution.

---

## 🏢 About

Developed by the **Geospatial & Remote Sensing team at [iForest Global](https://iforest.global)** for air quality and biomass burning research across India's agricultural regions.

If you use this pipeline in research or reporting, please cite:

```
iForest Global (2026). SEVIRI Geostationary Fire Detection Pipeline.
GitHub: https://github.com/YOUR_USERNAME/seviri-fire-detection
```

---

## 📚 References

- Wooster, M.J. et al. (2015). LSA SAF Meteosat FRP products. *Remote Sensing of Environment*.
- EUMETSAT LSA-SAF: https://landsaf.ipma.pt/
- Justice, C.O. et al. (2002). The MODIS fire products. *Remote Sensing of Environment*, 83(1–2).
- Vadrevu, K.P. et al. (2019). Spatial and temporal analysis of agricultural waste burning in South and Southeast Asia. *Nutr. Cycl. Agroecosystems*.

---

*For questions or bugs, open an [Issue](https://github.com/YOUR_USERNAME/seviri-fire-detection/issues).*
