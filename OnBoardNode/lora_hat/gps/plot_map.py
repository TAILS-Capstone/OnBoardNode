import pandas as pd
import folium
import argparse

def main():
    """Plot GPS coordinates on a map, filtered by detection label and deduplicated by second."""
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Plot coordinates on a map filtered by detection label')
    parser.add_argument('--csv_path', required=True, help='Path to the CSV file with coordinates')
    parser.add_argument('--detection_label', required=True, nargs='+', help='Label to filter points by')
    args = parser.parse_args()

    # Join the detection label parts if there were spaces
    detection_label = ' '.join(args.detection_label)

    # Load CSV file with the provided path
    df = pd.read_csv(args.csv_path)
    
    # Filter data by detection_label
    filtered_df = df[df['detection_label'] == detection_label]
    
    if filtered_df.empty:
        print(f"No points found with detection_label: {detection_label}")
        return

    # Convert timestamp to datetime and drop duplicates within the same second
    filtered_df['timestamp'] = pd.to_datetime(filtered_df['timestamp'])
    filtered_df = filtered_df.drop_duplicates(subset=['timestamp'], keep='first')
    
    if filtered_df.empty:
        print("No unique points found after removing duplicates")
        return

    # Compute the center of the map
    center_lat = filtered_df["latitude"].mean()
    center_lon = filtered_df["longitude"].mean()

    # Create a folium map centered on the data
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    # Add each point as a marker
    for _, row in filtered_df.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=3,
            color="blue",
            fill=True,
            fill_color="blue",
        ).add_to(m)

    # Save the map to an HTML file with the detection label in the filename
    output_file = f"map_{detection_label.replace(' ', '_')}.html"
    m.save(output_file)
    print(f"Map saved as {output_file} with {len(filtered_df)} unique points")

if __name__ == "__main__":
    main()
