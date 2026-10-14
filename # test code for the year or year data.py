# test code for the year or year data
# import folium

# m = folium.Map(location=[43.08, -73.78], zoom_start=12)

# parks = folium.FeatureGroup(name="Parks").add_to(m)
# schools = folium.FeatureGroup(name="Schools").add_to(m)

# folium.Marker([43.075, -73.79], popup="Congress Park").add_to(parks)
# folium.Marker([43.09, -73.77], popup="High School").add_to(schools)

# folium.LayerControl().add_to(m)   # checkbox panel to show/hide layers
# m.save("map2.html")

import os
import folium

m = folium.Map(location=[43.0831, -73.7846], zoom_start=13, tiles="CartoDB positron")
folium.Marker([43.0831, -73.7846], popup="Saratoga Springs").add_to(m)

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "map.html")
m.save(output_path)
print("Map saved to:", output_path)

os.startfile(output_path)   # opens the file in your default browser on Windows