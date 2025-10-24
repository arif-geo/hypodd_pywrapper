"""
Convert CSV phase picks to HypoDD input formats (.pha and .cc files)
"""

import numpy as np
import pandas as pd
import re
from datetime import datetime


def create_station_file(station_csv, output_file):
    """
    Create HypoDD station file from station CSV.
    
    Format: STA LAT LON ELV
    """
    df = pd.read_csv(station_csv)
    
    with open(output_file, 'w') as f:
        for _, row in df.iterrows():
            # Station code, lat, lon, elevation (in meters)
            f.write(f"{row['station']:7s} {row['latitude']:9.5f} {row['longitude']:10.5f} {row['elevation']:6.1f}\n")
    
    print(f"Created station file: {output_file} with {len(df)} stations")


def load_catalog(catalog_csv):
    """
    Load catalog from Yoon & Shelly CSV into dict format.
    
    Returns: dict {event_id: {'lat': x, 'lon': y, 'depth': z, 'mag': m, 'eh': ex, 'ez': ez}}
    """
    df = pd.read_csv(catalog_csv)
    catalog = {}
    
    for _, row in df.iterrows():
        event_id = str(row['event_id'])
        catalog[event_id] = {
            'lat': row['latitude'],
            'lon': row['longitude'],
            'depth': row['depth'],
            'mag': row['magnitude'],
            # Use uncertainties if available, otherwise 0.0
            'eh': row.get('uncertainty_x', 0.0) if pd.notna(row.get('uncertainty_x')) else 0.0,
            'ez': row.get('uncertainty_z', 0.0) if pd.notna(row.get('uncertainty_z')) else 0.0
        }
    
    print(f"Loaded catalog with {len(catalog)} events")
    return catalog


def create_event_id_mapping(csv_file, output_file='event_id_mapping.csv'):
    """
    Create mapping between original event_ids and synthetic integer IDs.
    
    Returns: dict {original_event_id: synthetic_id}
    """
    df = pd.read_csv(csv_file)
    unique_events = df['event_id'].unique()
    
    # Generate synthetic IDs (starting from 100,000)
    synthetic_ids = np.arange(100000, 100000 + len(unique_events))
    mapping_df = pd.DataFrame({
        'original_id': unique_events,
        'synthetic_id': synthetic_ids
    })
    mapping_df.to_csv(output_file, index=False)
    
    print(f"Created event ID mapping: {output_file}")
    print(f"Mapped {len(mapping_df)} events (IDs: 100000 to {100000 + len(mapping_df) - 1})")

    # Return as dict {original_event_id: synthetic_id}
    return mapping_df.set_index('original_id')['synthetic_id'].to_dict()


def csv_to_pha(csv_file, output_file, catalog_info=None, event_id_mapping=None, apply_lag_correction=False):
    """
    Convert CSV to .pha format.
    
    Format: # YR MO DY HR MN SC LAT LON DEP MAG EH EZ RMS ID
            STA TT WGHT PHA
    
    catalog_info: dict {event_id: {'lat': x, 'lon': y, 'depth': z, 'mag': m, 'eh': ex, 'ez': ez}}
    event_id_mapping: dict {original_event_id: synthetic_id} or None
    apply_lag_correction: If True, apply lag times to detected event travel times
                         (for catalog-only relocation method). Template events remain unchanged.
    """
    df = pd.read_csv(csv_file)
    unique_events = df['event_id'].unique()
    
    with open(output_file, 'w') as f:
        for event in unique_events:
            event_data = df[df['event_id'] == event].iloc[0]
            
            # Parse origin time from CSV
            dt = datetime.fromisoformat(event_data['origin_time'].replace('Z', '+00:00'))
            yr, mo, dy, hr, mn, sc = dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond/1e6
            
            # Initialize defaults
            lat, lon, depth, mag = 0.0, 0.0, 0.0, 0.0
            eh, ez = 0.0, 0.0
            
            # Strategy: Use catalog location if event is in catalog (template event)
            # Otherwise, use template's location for detected events
            if catalog_info and str(event) in catalog_info:
                # Template event - use catalog info directly
                cat = catalog_info[str(event)]
                lat, lon, depth = cat['lat'], cat['lon'], cat['depth']
                mag = cat['mag']
                eh, ez = cat['eh'], cat['ez']
            
            elif catalog_info and str(event_data['template_id']) in catalog_info:
                # Detected event - inherit template's location as initial guess
                cat = catalog_info[str(event_data['template_id'])]
                lat, lon, depth = cat['lat'], cat['lon'], cat['depth']
                
                # Note: For detected events, we inherit template location but:
                # - Magnitude is unknown (set to 0.0) - HypoDD will not estimate this
                # - Uncertainties set to 0.0 since we're using template's location as proxy
                # - HypoDD will relocate these events relative to template
                mag = 0.0
                eh, ez = 0.0, 0.0
            
            # Get synthetic ID for output
            if event_id_mapping is not None:
                event_id = event_id_mapping[event]
            else:
                event_id = event  # Fallback to original ID if no mapping provided

            # Write event header: YR MO DY HR MN SC LAT LON DEP MAG EH EZ RMS ID
            # Format matches ncsn2pha.f: (a1,i5,1x,i2,1x,i2,1x,i2,1x,i2,1x,f5.2,1x,
            #                              f8.4,1x,f9.4,1x,f7.2,f6.2,f6.2,f6.2,f6.2,1x,i10)
            # Note: i5 means 5 chars right-justified (includes leading space for 4-digit years)
            # RMS is set to 0.0 (will be computed by HypoDD)
            f.write(f"#{yr:5d} {mo:2d} {dy:2d} {hr:2d} {mn:2d} {sc:5.2f} "
                   f"{lat:8.4f} {lon:9.4f} {depth:7.2f}{mag:6.2f}{eh:6.2f}{ez:6.2f}{0.0:6.2f} {event_id:10d}\n")
            
            # Write phase picks: STA TT WGHT PHA
            picks = df[df['event_id'] == event]
            for _, pick in picks.iterrows():
                station = pick['station']
                
                # Determine if this is a detected event (not the template itself)
                is_detected_event = str(event) != str(pick['template_id'])
                
                # P-phase pick
                if pd.notna(pick['travel_time_p']):
                    tt_p = pick['travel_time_p']
                    
                    # Apply lag correction for detected events if requested
                    if apply_lag_correction and is_detected_event and pd.notna(pick['lag_time_p']):
                        tt_p += pick['lag_time_p']
                    
                    # Weight: use CC if available (detected events), otherwise 1.0 (template events)
                    wght = pick['cc_p'] if pd.notna(pick['cc_p']) else 1.0
                    f.write(f"{station:7s} {tt_p:8.3f} {wght:6.3f} P\n")
                
                # S-phase pick
                if pd.notna(pick['travel_time_s']):
                    tt_s = pick['travel_time_s']
                    
                    # Apply lag correction for detected events if requested
                    if apply_lag_correction and is_detected_event and pd.notna(pick['lag_time_s']):
                        tt_s += pick['lag_time_s']
                    
                    wght = pick['cc_s'] if pd.notna(pick['cc_s']) else 1.0
                    f.write(f"{station:7s} {tt_s:8.3f} {wght:6.3f} S\n")
    
    print(f"Created {output_file} with {len(unique_events)} events")


def csv_to_cc(csv_file, output_file, min_cc=0.0, event_id_mapping=None):
    """
    Convert CSV to .cc format.
    
    Format: # ID1 ID2 OTC
            STA DT WGHT PHA
    
    min_cc: minimum CC threshold
    event_id_mapping: dict {original_event_id: synthetic_id} or None to auto-generate
    """
    df = pd.read_csv(csv_file)
    detections = df[df['event_id'] != df['template_id']]
    
    if len(detections) == 0:
        detections = df.copy()
    
    pairs = detections[['event_id', 'template_id']].drop_duplicates()
    
    # Create mapping if not provided
    if event_id_mapping is None:
        all_events = pd.concat([detections['event_id'], detections['template_id']]).unique()
        event_id_mapping = {event: i for i, event in enumerate(all_events, start=1)}
    
    with open(output_file, 'w') as f:
        for _, pair in pairs.iterrows():
            picks = detections[(detections['event_id'] == pair['event_id']) & 
                             (detections['template_id'] == pair['template_id'])]
            
            # Get synthetic IDs
            id1 = event_id_mapping[pair['event_id']]
            id2 = event_id_mapping[pair['template_id']]
            
            # Collect valid picks
            valid_picks = []
            for _, pick in picks.iterrows():
                if pd.notna(pick['lag_time_p']) and pd.notna(pick['cc_p']) and pick['cc_p'] >= min_cc:
                    valid_picks.append((pick['station'], pick['lag_time_p'], pick['cc_p'], 'P'))
                if pd.notna(pick['lag_time_s']) and pd.notna(pick['cc_s']) and pick['cc_s'] >= min_cc:
                    valid_picks.append((pick['station'], pick['lag_time_s'], pick['cc_s'], 'S'))
            
            if valid_picks:
                f.write(f"# {id1:9d} {id2:9d} 0.000000\n")
                for sta, dt, wght, pha in valid_picks:
                    f.write(f"{sta:7s} {dt:9.6f} {wght:5.3f} {pha}\n")
    
    print(f"Created {output_file}")
