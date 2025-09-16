import pandas as pd
import folium
import sys
import argparse

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Plot GPS coordinates on a map, filtered by detection label')
    parser.add_argument('--csv', type=str, default="detections_log.csv", help='CSV file path')
    parser.add_argument('--label', type=str, default=None, help='Filter by detection label (e.g., "person")')
    args = parser.parse_args()

    # Load CSV file with detection data
    try:
        df = pd.read_csv(args.csv)
    except FileNotFoundError:
        print(f"Error: Could not find CSV file '{args.csv}'")
        sys.exit(1)
    
    # Check if required columns exist
    required_cols = ['latitude', 'longitude']
    if not all(col in df.columns for col in required_cols):
        print(f"Error: CSV must contain columns: {', '.join(required_cols)}")
        sys.exit(1)
    
    # Filter by detection_label if specified
    if args.label and 'detection_label' in df.columns:
        filtered_df = df[df['detection_label'] == args.label]
        if filtered_df.empty:
            print(f"No coordinates found with detection_label '{args.label}'")
            sys.exit(0)
        print(f"Plotting {len(filtered_df)} points with detection_label '{args.label}'")
        df = filtered_df
    else:
        if args.label:
            print("Warning: 'detection_label' column not found in CSV, plotting all points")
        print(f"Plotting {len(df)} points")

    # Compute the center of the map
    center_lat = df["latitude"].mean()
    center_lon = df["longitude"].mean()

    # Create a folium map centered on the data
    m = folium.Map(location=[center_lat, center_lon], zoom_start=15)

    # Add each point as a marker
    for _, row in df.iterrows():
        popup_text = f"Lat: {row['latitude']}, Lon: {row['longitude']}"
        
        # Add additional info to popup if available
        if 'detection_label' in row:
            popup_text += f"<br>Label: {row['detection_label']}"
        if 'confidence' in row:
            popup_text += f"<br>Confidence: {row['confidence']}"
        if 'timestamp' in row:
            popup_text += f"<br>Time: {row['timestamp']}"
            
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color="blue",
            fill=True,
            fill_color="blue",
            popup=popup_text
        ).add_to(m)

    # Add connecting line showing the path
    if len(df) > 1:
        folium.PolyLine(
            locations=df[["latitude", "longitude"]].values,
            color="red",
            weight=2,
            opacity=0.7
        ).add_to(m)

    # Save the map to an HTML file
    output_file = f"map{'_'+args.label if args.label else ''}.html"
    m.save(output_file)
    print(f"Map saved to {output_file}")

if __name__ == "__main__":
    main()
