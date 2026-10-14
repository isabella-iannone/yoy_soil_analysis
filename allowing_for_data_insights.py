# Creating an html that will allow for year over year to be calcualted

# importing libraries
import pandas as pd
import folium
from folium.plugins import TreeLayerControl
import json
import branca.colormap as cm
import os

# load in the data (this would be after people have selected the campaigns that they want to compare)

# field data
camp_data = pd.read_csv(r'C:\Users\isabe\year_or_year_testing_info\field_data_year_or_year_test.csv')

#  geojson data
camp_fields = pd.read_csv(r'C:\Users\isabe\year_or_year_testing_info\field_polygons_year_or_year_test.csv')


# test prints for loading in data
# print(camp_data.head())
# print(camp_fields)


# create map 

# number of campaigns
n_camp = len(pd.unique(camp_fields['campaign_id']))
print(n_camp)
print(pd.unique(camp_fields['campaign_id']))

# want to store a key value pair of ids and names of fields as well as campaign
list_camp_fields = camp_fields.set_index('campaign_field_id')['field_name'].to_dict()
print(list_camp_fields)



# creating the map
m = folium.Map(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
               attr="Tiles &copy; Esri")


# palette to use for the map
palette = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
           "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4"]


tree = {"label": "Campaigns", "select_all_checkbox": True, "children": []}
all_bounds = []

for i, (campaign_id, group) in enumerate(camp_fields.groupby("campaign_id")):
    campaign_name = group["campaign_name"].iloc[0]
    color = palette[i % len(palette)]
    swatch = f'<span style="display:inline-block;width:12px;height:12px;background:{color};margin-right:6px;border:1px solid #333"></span>'

    campaign_node = {"label": f"{swatch}{campaign_name}", "select_all_checkbox": True, "collapsed": True, "children": []}
    for _, f in group.iterrows():
        shape = folium.GeoJson(
            json.loads(f["geometry_geojson"]),
            name=f["field_name"],
            style_function=lambda x, c=color: {"color": c, "weight": 3, "fillColor": c, "fillOpacity": 0.15},
            tooltip=f"{f['field_name']} ({campaign_name})",
        ).add_to(m)
        campaign_node["children"].append({"label": str(f["field_name"]), "layer": shape})
        all_bounds.extend(shape.get_bounds())
    tree["children"].append(campaign_node)

TreeLayerControl(overlay_tree=tree).add_to(m)

lats = [b[0] for b in all_bounds]
lons = [b[1] for b in all_bounds]
m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])   # zoom to fit all fields

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "carbon_map.html")
m.save(output_path)
os.startfile(output_path)















# compare fields between the first and second campaign
# this is going to look similar to the mapping when uploading data in a csv

# while this is being selected there is a map that pop on the side and you can click on and off the two campaigns with the name and year attached 
# there should be a pop that allows for 
    # rank the fields that are closest in matching to each other 
    # provide to the user:
        # are these the correct fields to compare
            # Give a yes or no button 
                # if no select the correct field
                # OR
                # is this a historic field (no longer used)
                    # yes or no
                # has this field been split into dif fields
                    # give an area to have a drop down of the fields that can be split 
                    # add different sections that allow to add more field
                # has this field been merged into other fields



# keep this information stored





