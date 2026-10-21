# Creating an html that will allow for year over year to be calcualted

# importing libraries
# import pandas as pd
import folium
from folium.plugins import TreeLayerControl
import json
from folium.plugins.pattern import StripePattern
import branca.colormap as cm
# import os

# load in the data (this would be after people have selected the campaigns that they want to compare)

# # field data
# camp_data = pd.read_csv(r'C:\Users\isabe\year_or_year_testing_info\field_data_year_or_year_test.csv')

# #  geojson data
# camp_fields = pd.read_csv(r'C:\Users\isabe\year_or_year_testing_info\field_polygons_year_or_year_test.csv')


# # test prints for loading in data
# # print(camp_data.head())
# # print(camp_fields)


# # create map 

# # number of campaigns
# n_camp = len(pd.unique(camp_fields['campaign_id']))
# print(n_camp)
# print(pd.unique(camp_fields['campaign_id']))

# # want to store a key value pair of ids and names of fields as well as campaign
# list_camp_fields = camp_fields.set_index('campaign_field_id')['field_name'].to_dict()
# print(list_camp_fields)

def create_map(camp_fields):
    # creating the map
    # map tiles that are being used
    m = folium.Map(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Tiles &copy; Esri")

    dashes = [None, "8 4", "2 4", "12 4 2 4", "1 6"]
    angles = [45, -45, 0, 90, 30, -30, 60, -60, 15, -15]




    # palette to use for the map
    palette = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
            "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4"]


    # legend information
    tree = {"label": "Campaigns", "select_all_checkbox": True, "children": []}
    all_bounds = []

    # loop through the campaign ids and group
    for i, (campaign_id, group) in enumerate(camp_fields.groupby("campaign_id")):
        # goes to the first row in the campaign
        campaign_name = group["campaign_name"].iloc[0]
        # select color for campaign from palette
            # if more campaign than colors will start back at the begining of the palette
        color = palette[i % len(palette)]
        striped = i % 2 == 1
        dash = "8 4" if striped else None
        if striped:
            pattern = StripePattern(angle=angles[i % len(angles)], color=color, weight=2, space_weight=6, opacity=0.9, space_opacity=0)
            pattern.add_to(m)
            fill = {"fillPattern": pattern, "fillOpacity": 1.0}
            swatch_bg = f"repeating-linear-gradient(45deg,{color} 0 2px,transparent 2px 6px)"
        else:
            fill = {"fillColor": color, "fillOpacity": 0.3}
            swatch_bg = color
        style = {"color": color, "weight": 2 if striped else 5, "dashArray": dash, **fill}
        border = "dashed" if striped else "solid"
        swatch = f'<span style="display:inline-block;width:14px;height:14px;margin-right:6px;border:2px {border} {color};background:{swatch_bg}"></span>'

        # Color box, checkbox, start with campaigns folded, and adds the fields as the children for each campaign
        campaign_node = {"label": f"{swatch}{campaign_name}", "select_all_checkbox": True, "collapsed": True, "children": []}

        # inside the first loop 
            # loops through each field in the campaign
        for _, f in group.iterrows():
            # getting the GeoJson that was provided from the SQL query
            shape = folium.GeoJson(
                json.loads(f["geometry_geojson"]),
                # labels the polygon with the field name
                name=f["field_name"],
                # styling of the polygon
                style_function=lambda x, s=style: dict(s),
                # shows the name of the field when it is hovered over 
                tooltip=f"{f['field_name']} ({campaign_name})",
                # all this is than added to the map
            ).add_to(m)
            # adds the field to the correct campaign
            campaign_node["children"].append({"label": str(f["field_name"]), "layer": shape})
            # gets the corner of the fields, allows for the zoom to be set correctly
            all_bounds.extend(shape.get_bounds())
        # once all fields are done for the campaign it is added to the main tree
        tree["children"].append(campaign_node)

    # adds the collapsed legend to the map 
    TreeLayerControl(overlay_tree=tree).add_to(m)

    # zoom to the fit of the fields
    lats = [b[0] for b in all_bounds]
    lons = [b[1] for b in all_bounds]
    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])   # zoom to fit all fields

    print(type(m))

    return m

    #     output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "carbon_map_test.html")
    # map.save(output_path)
    # os.startfile(output_path)



