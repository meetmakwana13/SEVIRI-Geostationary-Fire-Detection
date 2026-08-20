import os
import glob
import re
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta, time, date
from matplotlib.ticker import FuncFormatter, PercentFormatter

# --- CONFIGURATION ---
DATA_DIR = r'C:\Users\iForest.Global\OneDrive - INTERNATIONAL FORUM FOR ENVIRONMENT SCIENCE & TECHNOLOGY (iFOREST)\Desktop\sevari\15Feb_16May_2019-2026\2026'
DATA_DIR_OUTPUT = r'C:\Users\iForest.Global\OneDrive - INTERNATIONAL FORUM FOR ENVIRONMENT SCIENCE & TECHNOLOGY (iFOREST)\Desktop\sevari\15Feb_16May_2019-2026\2026\output_2'
FILE_PATTERN = '*.NAT'

# --- DATE FILTER CONFIGURATION ---
# Define the date range for your analysis (Format: YYYY, MM, DD)
START_DATE = date(2026, 3, 1)                                                                                                           
END_DATE = date(2026, 6, 30)

# District Shapefile (Ensure this contains both 'District' and 'State' columns)       
SHAPEFILE_PATH = r'C:\Users\iForest.Global\OneDrive - INTERNATIONAL FORUM FOR ENVIRONMENT SCIENCE & TECHNOLOGY (iFOREST)\Desktop\Shapefile\District Boundary\District_NWIC.shp'
DIST_COL = 'District'
STATE_COL = 'State'

# Create output directory  
if not os.path.exists(DATA_DIR_OUTPUT):
    os.makedirs(DATA_DIR_OUTPUT)

STATE_MAPPING = {'PB': 'Punjab', 'HR': 'Haryana', 'UP': 'Uttar Pradesh', 'MP': 'Madhya Pradesh'}
STATE_COLORS = {'PB': 'blue', 'HR': 'red', 'UP': 'green', 'MP': 'purple'}
BAR_COLOR = '#de525f' 

USE_REPORTED_WINDOWS = False

# Define "Reported" Time Windows (IST)
REPORTED_WINDOWS = [
    (time(0, 30), time(2, 30)),
    (time(10, 30), time(15, 0))
]

def is_time_reported(check_time):
    # If the toggle is off, treat every timestamp as "reported"
    if not USE_REPORTED_WINDOWS:
        return True
        
    # If the toggle is on, check against the specific windows
    for start, end in REPORTED_WINDOWS:
        if start <= check_time <= end:
            return True
    return False

def extract_cap_data(filepath):
    """Extracts timestamp and fire coordinates from .NAT (XML-based) files."""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        eff_match = re.search(rb'<effective>(.*?)</effective>', content)
        if not eff_match: return None, []
        
        ts_str = eff_match.group(1).decode('utf-8')
        utc_ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        ist_ts = utc_ts + timedelta(hours=5, minutes=30)
        
        xml_content = content.decode('utf-8', errors='ignore')
        matches = re.findall(r'<circle>([\d\.\-,\s]+)</circle>', xml_content)
        fires = [Point(float(m.strip().split()[0].split(',')[1]), 
                       float(m.strip().split()[0].split(',')[0])) for m in matches]
        return utc_ts, ist_ts, fires
    except Exception as e:
        print(f"Error reading {os.path.basename(filepath)}: {e}")
        return None, []

# def add_satellite_annotations(ax):
#     """Adds vertical lines indicating major LEO satellite overpass times."""
#     for idx, label in [(21, 'MODIS (Terra)\n10:30'), (27, 'MODIS (Aqua), VIIRS\n13:30')]:
#         ax.axvline(x=idx, color='black', linestyle='--', alpha=0.6, linewidth=1.2)
#         ax.text(idx - 0.4, ax.get_ylim()[1]*0.7, label, rotation=90, 
#                 fontweight='bold', fontsize=11, ha='right', va='center')

def add_satellite_annotations(ax):
    # Added (3, 'VIIRS\n01:30') for the new satellite line
    for idx, label in [(3, 'VIIRS\n01:30'), (21, 'MODIS (Terra)\n10:30'), (27, 'MODIS (Aqua), VIIRS\n13:30')]:
        ax.axvline(x=idx, color='black', linestyle='--', alpha=0.6, linewidth=1.2)
        ax.text(idx - 0.4, ax.get_ylim()[1]*0.7, label, rotation=90, 
                fontweight='bold', fontsize=11, ha='right', va='center')

def plot_all_trends(df, full_range, x_vals, x_labels):
    """Generates Count, Percentage, and Combined trend charts."""
    df['Time_IST'] = df['IST_Timestamp'].dt.floor('30min').dt.time
    
    # 1. Individual State Charts
    for code, full_name in STATE_MAPPING.items():
        col = f'{code}_Count'
        if col not in df.columns: continue
        
        hourly = df.groupby('Time_IST')[col].sum().reindex(full_range, fill_value=0)
        total_fires = hourly.sum()
        
        # --- COUNT BAR CHART ---
        fig, ax = plt.subplots(figsize=(18, 8))
        ax.bar(x_vals, hourly.values, color=BAR_COLOR, alpha=0.9)
        add_satellite_annotations(ax)
        ax.set_xticks(x_vals)
        ax.set_xticklabels(x_labels, rotation=90, fontsize=16)
        ax.set_title(f"Diurnal Fire Cycle - {full_name} (IST Count)", fontsize=15, fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(DATA_DIR_OUTPUT, f'Trend_Count_{code}.png'), dpi=150)
        plt.close()

        # --- PERCENTAGE BAR CHART ---
        if total_fires > 0:
            fig, ax = plt.subplots(figsize=(18, 8))
            hourly_perc = (hourly / total_fires * 100)
            ax.bar(x_vals, hourly_perc.values, color=BAR_COLOR, alpha=0.9)
            add_satellite_annotations(ax)
            ax.set_xticks(x_vals)
            ax.set_xticklabels(x_labels, rotation=90, fontsize=16)
            ax.yaxis.set_major_formatter(PercentFormatter())
            ax.set_title(f"Diurnal Activity Pulse - {full_name} (%)", fontsize=15, fontweight='bold')
            plt.tight_layout()
            plt.savefig(os.path.join(DATA_DIR_OUTPUT, f'Trend_Perc_{code}.png'), dpi=150)
            plt.close()

    # 2. Combined Trends (Line Plots)
    for mode in ['Count', 'Perc']:
        fig, ax = plt.subplots(figsize=(18, 9))
        for code, full_name in STATE_MAPPING.items():
            hourly = df.groupby('Time_IST')[f'{code}_Count'].sum().reindex(full_range, fill_value=0)
            if mode == 'Perc':
                total = hourly.sum()
                if total == 0: continue
                data_to_plot = (hourly / total * 100)
            else:
                data_to_plot = hourly.values
                
            ax.plot(x_vals, data_to_plot, marker='o', markersize=3, linewidth=2, 
                    label=full_name, color=STATE_COLORS.get(code, 'black'))
        
        add_satellite_annotations(ax)
        ax.set_xticks(x_vals)
        ax.set_xticklabels(x_labels, rotation=90, fontsize=16)
        if mode == 'Perc': ax.yaxis.set_major_formatter(PercentFormatter())
        ax.set_title(f"Combined Diurnal Fire Cycle - All States ({mode})", fontsize=16, fontweight='bold')
        ax.legend(loc='upper right')
        plt.tight_layout()
        plt.savefig(os.path.join(DATA_DIR_OUTPUT, f'Combined_Trend_{mode}.png'), dpi=200)
        plt.close()

def analyze_fires():
    # Load Geodata
    dist_gdf = gpd.read_file(SHAPEFILE_PATH).to_crs("EPSG:4326")
    
    files = sorted(glob.glob(os.path.join(DATA_DIR, FILE_PATTERN)))
    all_records = []      # For Sheet 1
    district_logs = []    # For Sheet 3
    all_fire_geometries = [] # For Spatial Map

    print(f"Processing {len(files)} files...")

    for f in files:
        utc_ts, ist_ts, fire_pts = extract_cap_data(f)
        
        if ist_ts is None: continue
        
        # The UTC date naturally groups your 05:30 IST to 05:29 IST cycle!
        logical_date = utc_ts.date() 
        
        if not (START_DATE <= logical_date <= END_DATE):
            continue 
            
        rec = {'IST_Timestamp': ist_ts, 'Date': logical_date, 'Time': ist_ts.time()}
        if fire_pts:
            fgdf = gpd.GeoDataFrame(geometry=fire_pts, crs="EPSG:4326")
            joined = gpd.sjoin(fgdf, dist_gdf, how="inner", predicate="within")
            
            # Update counts for Sheet 1
            counts = joined[STATE_COL].value_counts()
            for code in STATE_MAPPING.keys():
                rec[f'{code}_Count'] = counts.get(code, 0)
            
            # Log individual fires for Sheet 3 and Map
            for _, row in joined.iterrows():
                all_fire_geometries.append({'geometry': row.geometry, 'State': row[STATE_COL]})
                district_logs.append({
                    'Date': logical_date,  # <-- Change ist_ts.date() to logical_date
                    'Time': ist_ts.strftime('%H:%M'),
                    'State': row[STATE_COL],
                    'District': row[DIST_COL],
                    'Fire_Count': 1
                })
        else:
            for code in STATE_MAPPING.keys(): rec[f'{code}_Count'] = 0
            
        all_records.append(rec)

    if not all_records: 
        print(f"No fire data found between {START_DATE} and {END_DATE}.")
        return

    df = pd.DataFrame(all_records)
    df_dist = pd.DataFrame(district_logs)

    # --- SHEET 2: STATISTICAL SUMMARY ---
    summary_data = []
    for code, full_name in STATE_MAPPING.items():
        col = f'{code}_Count'
        state_activity = df[df[col] > 0].copy()
        total_fires = df[col].sum()
        
        if total_fires == 0: continue
        
        # Calculate Peak and Earliest
        hourly_series = df.groupby(df['IST_Timestamp'].dt.floor('30min').dt.time)[col].sum()
        peak_hour = hourly_series.idxmax().strftime('%H:%M')
        earliest = state_activity['Time'].min()
        
        # Robust Unreported Logic: Check every row's time against the windows
        reported_fires = 0
        for idx, row in df.iterrows():
            if is_time_reported(row['Time']):
                reported_fires += row[col]
        
        unreported_pct = ((total_fires - reported_fires) / total_fires) * 100
        
        summary_data.append({
            'State': full_name,
            'Total Fires': total_fires,
            'Earliest Detection': earliest,
            'Peak Fire Hour': peak_hour,
            'Unreported Data (%)': f"{unreported_pct:.2f}%"
        })
    df_summary = pd.DataFrame(summary_data)

    # --- EXPORT EXCEL ---
    excel_path = os.path.join(DATA_DIR_OUTPUT, 'Fire_Analysis_Robust_Report.xlsx')
    with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
        # Sheet 1
        df_sheet1 = df.copy()
        df_sheet1['IST_Timestamp'] = df_sheet1['IST_Timestamp'].dt.tz_localize(None)
        cols = ['Date', 'Time'] + [c for c in df_sheet1.columns if 'Count' in c]
        df_sheet1[cols].to_excel(writer, sheet_name='Daily_Trend_Report', index=False)
        
        # Sheet 2
        df_summary.to_excel(writer, sheet_name='Statistical_Summary', index=False)
        
        # Sheet 3
        if not df_dist.empty:
            df_dist_final = df_dist.groupby(['State', 'District', 'Date', 'Time']).sum().reset_index()
            df_dist_final.to_excel(writer, sheet_name='District_Wise_Report', index=False)

    # --- PLOTTING ---
    full_range = [datetime.strptime(f"{h:02d}:{m:02d}", "%H:%M").time() for h in range(24) for m in [0, 30]]
    x_labels = [t.strftime('%H:%M') for t in full_range]
    plot_all_trends(df, full_range, range(len(full_range)), x_labels)

    # --- SPATIAL MAP ---
    if all_fire_geometries:
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # Filter shapefile to focus on target states
        focus_states = dist_gdf[dist_gdf[STATE_COL].isin(STATE_MAPPING.keys())]
        
        # 1. Plot District Boundaries (Lighter, thinner outline)
        focus_states.plot(ax=ax, color='white', edgecolor='#a0a0a0', linewidth=0.5, zorder=1)
        
        # 2. Dissolve into State Boundaries and Plot (Darker, thicker outline)
        state_boundaries = focus_states.dissolve(by=STATE_COL)
        state_boundaries.boundary.plot(ax=ax, edgecolor='black', linewidth=1.5, zorder=2)
        
        fires_gdf = gpd.GeoDataFrame(all_fire_geometries, crs="EPSG:4326")
        for code, color in STATE_COLORS.items():
            state_data = fires_gdf[fires_gdf['State'] == code]
            if not state_data.empty:
                # Plot fire points on top (zorder=3)
                state_data.plot(ax=ax, color=color, markersize=10, label=f"{code} ({len(state_data)})", alpha=0.6, zorder=3)
        
        plt.legend()
        plt.title(f"Spatial Fire Distribution (IST Snapshot)\n{START_DATE} to {END_DATE}")
        
        # Remove axes for a cleaner map look
        ax.set_axis_off() 
        
        plt.savefig(os.path.join(DATA_DIR_OUTPUT, 'Combined_Spatial_Map.png'), bbox_inches='tight', dpi=300)

    print(f"Success! Analysis complete. Files saved in: {DATA_DIR_OUTPUT}")

if __name__ == "__main__":
    analyze_fires()
