import pandas as pd
import folium

# Load CSV file; assume it has columns 'latitude' and 'longitude'
df = pd.read_csv("coordinates.csv")

# Compute the center of the map (optional)
center_lat = df["latitude"].mean()
center_lon = df["longitude"].mean()

# Create a folium map centered on the data
m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

# Add each point as a marker (or circle marker)
for _, row in df.iterrows():
    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=3,
        color="blue",
        fill=True,
        fill_color="blue",
    ).add_to(m)

# Save the map to an HTML file and open it in your browser
m.save("map.html")
