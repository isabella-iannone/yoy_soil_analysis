# Creating a folium map

import folium
from folium.plugins import TreeLayerControl
from folium.plugins.pattern import StripePattern
# import branca.colormap as cm


TILES = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
TILES_ATTR = "Tiles &copy; Esri"

PALETTE = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
            "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4"]

STRIPE_ANGLES = [45, -45, 0, 90, 30, -30, 60, -60, 15, -15]


def _campaign_style(i, m):
    # creating the map

    color = PALETTE[i % len(PALETTE)]
    striped = i % 2 == 1

    if striped:
        pattern = StripePattern(angle=STRIPE_ANGLES[i%len(STRIPE_ANGLES)], color=color, weight=2, space_weight=6, opacity=0.9, space_opacity=0)

        pattern.add_to(m)
        fill = {"fillPattern": pattern, "fillOpacity": 1.0}
        swatch_bg = f"repeating-linear-gradient(45deg,{color} 0 2px,transparent 2px 6px)"
    else:
        fill = {"fillColor": color, "fillOpacity": 0.3}
        swatch_bg = color
 
    style = {"color": color, "weight": 2 if striped else 5,
             "dashArray": "8 4" if striped else None, **fill}
    border = "dashed" if striped else "solid"
    swatch = (f'<span style="display:inline-block;width:14px;height:14px;margin-right:6px;'
              f'border:2px {border} {color};background:{swatch_bg}"></span>')
    return style, swatch

def create_map(fields_gdf):
    # map for every field and grouped by campaign in a legend

    if fields_gdf.empty:
        raise ValueError("create_map received no fields")
 
    m = folium.Map(tiles=TILES, attr=TILES_ATTR)
    # Remove the outline browsers draw around a clicked polygon
    m.get_root().header.add_child(folium.Element(
        "<style>.leaflet-interactive:focus { outline: none; }</style>"
    ))
 
    tree = {"label": "Campaigns", "select_all_checkbox": True, "children": []}
 
    for i, (_, group) in enumerate(fields_gdf.groupby("campaign_id")):
        campaign_name = group["campaign_name"].iloc[0]
        style, swatch = _campaign_style(i, m)
 
        # Campaign starts folded; its fields are the children
        campaign_node = {"label": f"{swatch}{campaign_name}", "select_all_checkbox": True,
                         "collapsed": True, "children": []}
 
        for _, f in group.iterrows():
            shape = folium.GeoJson(
                f.geometry.__geo_interface__,
                name=f["field_name"],
                style_function=lambda x, s=style: dict(s),
                tooltip=f"{f['field_name']} ({campaign_name})",
            ).add_to(m)
            campaign_node["children"].append({"label": str(f["field_name"]), "layer": shape})
 
        tree["children"].append(campaign_node)
 
    TreeLayerControl(overlay_tree=tree, collapsed=False).add_to(m)
 
    # Zoom to fit every field
    minx, miny, maxx, maxy = fields_gdf.total_bounds
    m.fit_bounds([[miny, minx], [maxy, maxx]])
 
    return m



