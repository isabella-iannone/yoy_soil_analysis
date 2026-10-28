# Creating a folium map

import folium
from folium.plugins import TreeLayerControl
from folium.plugins.pattern import StripePattern
import branca.colormap as cm
import geopandas as gpd
from folium import Element
from load_data import to_gdf
from branca.colormap import LinearColormap
from matplotlib.colors import LinearSegmentedColormap, Normalize
from scipy.spatial import cKDTree
import shapely
import pandas as pd
import numpy as np

# from folium.plugins import HeatMap
# import streamlit as st


TILES = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
TILES_ATTR = "Tiles &copy; Esri"

PALETTE = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
            "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4"]

STRIPE_ANGLES = [45, -45, 0, 90, 30, -30, 60, -60, 15, -15]

CARBON_COLORS = ["#1414ff", "#5ff5f5", "#f5f550", "#f04a1e"]  # blue -> cyan -> yellow -> red
CARBON_CMAP = LinearSegmentedColormap.from_list("carbon", CARBON_COLORS)

CHANGE_COLORS = ["#d7191c", "#fdae61", "#ffffbf", "#a6d96a", "#1a9641"]  # loss -> no change -> gain
CHANGE_CMAP = LinearSegmentedColormap.from_list("change", CHANGE_COLORS)

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
    bounds = [[miny, minx], [maxy, miny]]
    m.fit_bounds([[miny, minx], [maxy, maxx]])

    map_var = m.get_name()
    m.get_root().script.add_child(Element(f"""
        function refit() {{
            {map_var}.invalidateSize();
            {map_var}.fitBounds({bounds});
        }}
        window.addEventListener('load', refit);
        window.addEventListener('resize', refit);
    """))
 
    return m

# need only the matches w/out ignore as well as the SSURGO information
def create_heat_map(samples, fields, matches, SSURGO, vmin, vmax):
    # samples_gdf = st.session_state.get("samples_gdf")
    # fields_gdf = st.session_state.get("fields_gdf")
    # ssurgo_polys = st.session_state.get("ssurgo_polys")
    # matches = st.session_state.get("matches")

    # need to get the samples that are not being ignored
    # TODO need to think of how this logic will change when there are fields that are not perfect
    # TODO want each campaign to be a different map entirely
    keys = (
        matches[["campaign_id", "field_id"]]
        .drop_duplicates()
        .rename(columns={
            "campaign_id": "organization_campaign_id",
            "field_id": "field_id",
        })
    )

    samples = samples.merge(keys, on=["organization_campaign_id", "field_id"])
    samples = samples.dropna(subset=["latitude", "longitude"])

    field_keys = matches[["campaign_id", "field_id"]].drop_duplicates()

    # get the polygon/geodataframe for the fields using keys
    fields = fields.merge(field_keys, on=["campaign_id", "field_id"])
    # print(fields)
    fields = to_gdf(fields)
    # get the sample point using keys
    # samples = samples.merge(keys, on=["organization_campaign_id", "fields_id"])
    

    n = folium.Map(tiles=TILES, attr=TILES_ATTR)
    # get the SSURGO data that is correlated with these points 

    # if SSURGO is not None:
    #     folium.GeoJson(
    #         SSURGO.to_crs(epsg=4326)[["mukey", "geometry"]],
    #         name="SSURGO soils",
    #         style_function=lambda f: {"color": "#8B4513", "weight": 1, "fillOpacity": 0.1},
    #         tooltip=folium.GeoJsonTooltip(["mukey"]),
    #     ).add_to(n)

    # Matched field boundaries
    folium.GeoJson(
        fields[["field_name", "campaign_name", "geometry"]],
        name="Matched fields",
        style_function=lambda f: {"color": "#2c7be5", "weight": 2, "fillOpacity": 0},
        tooltip=folium.GeoJsonTooltip(["field_name", "campaign_name"]),
    ).add_to(n) 

    scale_max = max(samples["total_carbon_pct"])
    

    # Sample heat layer: density of samples, or weighted by a sample value
    # Sample heat layer: density of samples, or weighted by a sample value
    has_carbon = samples["total_carbon_pct"].notna()

    if has_carbon.any():
        s = samples[has_carbon].dropna(subset=["latitude", "longitude"])
        weights = s["total_carbon_pct"] / scale_max if scale_max else s["total_carbon_pct"]
        data = list(zip(s["latitude"], s["longitude"], weights.astype(float)))
    else:
        data = samples[["latitude", "longitude"]].dropna().values.tolist()

    add_idw_layer(n, samples, fields, "total_carbon_pct", vmin, vmax)
    minx, miny, maxx, maxy = fields.total_bounds
    n.fit_bounds([[miny, minx], [maxy, maxx]])
    return n

def idw(x, y, z, gx, gy, power=2, k=12):
    """Estimate values at grid points from the k nearest samples."""
    k = min(k, len(z))
    d, idx = cKDTree(np.column_stack([x, y])).query(
        np.column_stack([gx.ravel(), gy.ravel()]), k=k
    )
    if k == 1:
        d, idx = d[:, None], idx[:, None]
    w = 1.0 / np.maximum(d, 1e-12) ** power
    return ((w * z[idx]).sum(axis=1) / w.sum(axis=1)).reshape(gx.shape)

def add_idw_layer(m, samples, fields, value_col, vmin, vmax,
                  cells=250, name="Total Carbon (%)"):
    norm = Normalize(vmin=vmin, vmax=vmax)
    pts = samples[samples[value_col].notna()]
    pts = pts.set_geometry(pts.geometry.representative_point())

    layer = folium.FeatureGroup(name=name)
    for geom in fields.geometry:
        # Only use samples inside this field so values don't bleed between fields
        inside = pts[pts.within(geom.buffer(1e-5))]
        if inside.empty:
            continue

        minx, miny, maxx, maxy = geom.bounds
        coslat = np.cos(np.radians((miny + maxy) / 2))  # correct lon/lat distance
        nx = max(2, int(cells * (maxx - minx) * coslat / (maxy - miny)))
        gx, gy = np.meshgrid(np.linspace(minx, maxx, nx),
                             np.linspace(miny, maxy, cells))

        z = idw(inside.geometry.x.values * coslat, inside.geometry.y.values,
                inside[value_col].astype(float).values, gx * coslat, gy)

        # Clip to the field: blank out every grid cell outside the polygon
        z[~shapely.contains_xy(geom, gx, gy)] = np.nan

        rgba = CARBON_CMAP(norm(z))
        rgba[..., 3] = np.where(np.isnan(z), 0, 0.85)  # transparent outside field

        folium.raster_layers.ImageOverlay(
            image=np.flipud(rgba),               # image rows run north to south
            bounds=[[miny, minx], [maxy, maxx]],
            mercator_project=True,
        ).add_to(layer)
    layer.add_to(m)

    # Black field outlines on top
    folium.GeoJson(
        fields[["geometry"]], name="Fields",
        style_function=lambda _: {"color": "black", "weight": 2.5, "fill": False},
    ).add_to(m)

    # Color bar legend
    LinearColormap(CARBON_COLORS, vmin=vmin, vmax=vmax,
                   caption=name).add_to(m)

def create_change_map(samples_a, samples_b, fields_a, fields_b,
                      value_col="total_carbon_pct", cells=250):
    """Map of (year B - year A), clipped to the area farmed in both years."""

    def prep(s):
        s = s[s[value_col].notna()]
        return s.set_geometry(s.geometry.representative_point())

    pts_a, pts_b = prep(samples_a), prep(samples_b)

    # Interpolate both years on a shared grid for each field overlap
    pieces = []
    for fa in fields_a.geometry:
        for fb in fields_b.geometry:
            overlap = fa.intersection(fb).buffer(0)
            if overlap.is_empty or overlap.area < 1e-9:
                continue
            in_a = pts_a[pts_a.within(fa.buffer(1e-5))]
            in_b = pts_b[pts_b.within(fb.buffer(1e-5))]
            if in_a.empty or in_b.empty:
                continue

            minx, miny, maxx, maxy = overlap.bounds
            coslat = np.cos(np.radians((miny + maxy) / 2))
            nx = max(2, int(cells * (maxx - minx) * coslat / (maxy - miny)))
            gx, gy = np.meshgrid(np.linspace(minx, maxx, nx),
                                 np.linspace(miny, maxy, cells))

            def surface(p):
                return idw(p.geometry.x.values * coslat, p.geometry.y.values,
                           p[value_col].astype(float).values, gx * coslat, gy)

            diff = surface(in_b) - surface(in_a)
            diff[~shapely.contains_xy(overlap, gx, gy)] = np.nan
            pieces.append((diff, [[miny, minx], [maxy, maxx]]))

    m = folium.Map(tiles="Esri.WorldImagery")  # match the tiles your other maps use

    # Symmetric scale so "no change" is always the middle color
    lim = max((np.nanmax(np.abs(d)) for d, _ in pieces), default=0) or 0.1
    norm = Normalize(vmin=-lim, vmax=lim)

    layer = folium.FeatureGroup(name="Change in Total Carbon")
    for diff, bounds in pieces:
        rgba = CHANGE_CMAP(norm(diff))
        rgba[..., 3] = np.where(np.isnan(diff), 0, 0.85)
        folium.raster_layers.ImageOverlay(
            image=np.flipud(rgba), bounds=bounds, mercator_project=True
        ).add_to(layer)
    layer.add_to(m)

    # Outlines: baseline dashed white, second year solid black
    folium.GeoJson(fields_a[["geometry"]], name="Baseline fields",
                   style_function=lambda _: {"color": "white", "weight": 2,
                                             "dashArray": "6 4", "fill": False}).add_to(m)
    folium.GeoJson(fields_b[["geometry"]], name="Second-year fields",
                   style_function=lambda _: {"color": "black", "weight": 2.5,
                                             "fill": False}).add_to(m)

    LinearColormap(CHANGE_COLORS, vmin=-lim, vmax=lim,
                   caption="Change in Total Carbon (% points)").add_to(m)

    minx, miny, maxx, maxy = pd.concat([fields_a, fields_b]).total_bounds
    m.fit_bounds([[miny, minx], [maxy, maxx]])
    folium.LayerControl().add_to(m)
    return m