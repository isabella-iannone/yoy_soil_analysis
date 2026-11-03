
import folium
from folium.plugins import TreeLayerControl
from folium.plugins.pattern import StripePattern
import branca.colormap as cm
import geopandas as gpd
from folium import Element
from load_data import to_gdf
from branca.colormap import LinearColormap
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_hex
from scipy.spatial import cKDTree
from shapely.ops import unary_union
import shapely
import pandas as pd
import numpy as np
 
 
TILES = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
TILES_ATTR = "Tiles &copy; Esri"
 
PALETTE = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
            "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4"]
 
STRIPE_ANGLES = [45, -45, 0, 90, 30, -30, 60, -60, 15, -15]
 
CARBON_COLORS = ["#1414ff", "#5ff5f5", "#f5f550", "#f04a1e"]  # blue -> cyan -> yellow -> red
CARBON_CMAP = LinearSegmentedColormap.from_list("carbon", CARBON_COLORS)
 
CHANGE_COLORS = ["#d7191c", "#fdae61", "#ffffbf", "#a6d96a", "#1a9641"]  # loss -> no change -> gain
CHANGE_CMAP = LinearSegmentedColormap.from_list("change", CHANGE_COLORS)
 
# Border and point styles. Use STYLE_A for the earlier year and STYLE_B for the
# later year on every map, so a year looks the same wherever it appears.
STYLE_A = {"edge": "white", "dash": "6 4", "point_dash": "3 3"}
STYLE_B = {"edge": "black", "dash": None, "point_dash": None}
 
 
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
    bounds = [[miny, minx], [maxy, maxx]]   # was [maxy, miny]
    m.fit_bounds(bounds)
 
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
 
 
# ---------------------------------------------------------------------------
# Shared pieces for the year maps and the change map
# ---------------------------------------------------------------------------
 
def _base_map():
    # control=False keeps the imagery out of the legend (otherwise the tile URL
    # shows up there as a base-layer option)
    m = folium.Map(tiles=None)
    folium.TileLayer(TILES, attr=TILES_ATTR, name="Satellite", control=False).add_to(m)
    m.get_root().header.add_child(folium.Element("""<style>
        .leaflet-interactive:focus { outline: none; }
        /* Compact legend so it doesn't cover the fields on narrow maps */
        .leaflet-control-layers { font: 12px/1.3 sans-serif; border-radius: 6px; }
        .leaflet-control-layers-expanded { padding: 4px 8px; }
        .leaflet-control-layers-overlays label { margin: 1px 0; white-space: nowrap; }
        .leaflet-control-layers-overlays input { margin: 0 4px 0 0; }
        .leaflet-control-layers-base, .leaflet-control-layers-separator { display: none; }
    </style>"""))
    return m
 
 
def _prep_points(samples, value_col):
    pts = samples[samples[value_col].notna()].copy()
    return pts.set_geometry(pts.geometry.representative_point())
 
 
def _grid_surface(pts, values, geom, cells):
    """IDW of values at pts on a grid clipped to geom. Returns (grid, bounds)."""
    minx, miny, maxx, maxy = geom.bounds
    coslat = np.cos(np.radians((miny + maxy) / 2))  # correct lon/lat distance
    nx = max(2, int(cells * (maxx - minx) * coslat / (maxy - miny)))
    gx, gy = np.meshgrid(np.linspace(minx, maxx, nx),
                         np.linspace(miny, maxy, cells))
    z = idw(pts.geometry.x.values * coslat, pts.geometry.y.values,
            np.asarray(values, dtype=float), gx * coslat, gy)
    # Clip: blank out every grid cell outside the polygon
    z[~shapely.contains_xy(geom, gx, gy)] = np.nan
    return z, [[miny, minx], [maxy, maxx]]
 
 
def _add_raster(layer, z, bounds, cmap, norm):
    rgba = cmap(norm(z))
    rgba[..., 3] = np.where(np.isnan(z), 0, 0.85)  # transparent outside field
    folium.raster_layers.ImageOverlay(
        image=np.flipud(rgba),               # image rows run north to south
        bounds=bounds,
        mercator_project=True,
    ).add_to(layer)
 
 
# Muted categorical colors for soil map units (like the FieldVision soil layer)
SOIL_COLORS = ["#8e3b7e", "#c8664a", "#d8c8d8", "#e07b39", "#b8322a",
               "#6b4c9a", "#a0522d", "#f2a65a", "#5c8a8a", "#c9a227",
               "#7a9a4a", "#9c6b98"]
 
 
def _add_soils(m, SSURGO, fields_list, show=False):
    """'Soil Types' toggle: SSURGO map units clipped to the fields, each soil
    filled with its own color and outlined in white."""
    if SSURGO is None or SSURGO.empty:
        return
    soils = SSURGO.to_crs(epsg=4326)
    key = "muname" if "muname" in soils.columns else "mukey"
 
    # Colors are assigned from the full SSURGO table *before* clipping, so the
    # same soil gets the same color on every map
    units = sorted(soils[key].astype(str).unique())
    color_of = {u: SOIL_COLORS[i % len(SOIL_COLORS)] for i, u in enumerate(units)}
 
    area = unary_union([g for f in fields_list for g in f.geometry])
    soils = soils.clip(area)
    soils = soils[~soils.is_empty]
    if soils.empty:
        return
    soils = soils.assign(_color=soils[key].astype(str).map(color_of))
    cols = [c for c in ("muname", "mukey") if c in soils.columns]
 
    folium.GeoJson(
        soils[cols + ["_color", "geometry"]],
        name="Soil Types",
        show=show,
        style_function=lambda f: {"color": "white", "weight": 1.5,
                                  "fillColor": f["properties"]["_color"],
                                  "fillOpacity": 0.65},
        highlight_function=lambda _: {"weight": 3, "fillOpacity": 0.8},
        tooltip=folium.GeoJsonTooltip(cols, aliases=["Soil:", "Map unit:"][:len(cols)]),
    ).add_to(m)
 
 
def _add_border(m, fields, name, style, show=True):
    folium.GeoJson(
        fields[["geometry"]], name=name, show=show,
        style_function=lambda _, s=style: {"color": s["edge"], "weight": 2.5,
                                           "dashArray": s["dash"], "fill": False},
    ).add_to(m)
 
 
def _add_points(m, pts, value_col, norm, name, label, style, show=True):
    """Sample points colored on the carbon scale, value shown on hover."""
    layer = folium.FeatureGroup(name=name, show=show)
    for geom, v in zip(pts.geometry, pts[value_col].astype(float)):
        folium.CircleMarker(
            [geom.y, geom.x], radius=5, color=style["edge"], weight=2,
            dash_array=style["point_dash"], fill=True,
            fill_color=to_hex(CARBON_CMAP(norm(v))), fill_opacity=0.95,
            tooltip=f"{label}: {v:.2f}%",
        ).add_to(layer)
    layer.add_to(m)
 
 
def _finish(m, fields_list):
    minx, miny, maxx, maxy = pd.concat(fields_list).total_bounds
    m.fit_bounds([[miny, minx], [maxy, maxx]], padding=(20, 20))
    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    return m
 
 
# ---------------------------------------------------------------------------
# Maps 1 and 2: one campaign / year
# ---------------------------------------------------------------------------
 
# need only the matches w/out ignore as well as the SSURGO information
def create_heat_map(samples, fields, matches, SSURGO, vmin, vmax,
                    label="Total Carbon", style=STYLE_B,
                    show_points=True, show_soils=False):
    """One year's map. Legend: TC Surface, TC Points, Border, Soil Types."""
    keys = (
        matches[["campaign_id", "field_id"]]
        .drop_duplicates()
        .rename(columns={"campaign_id": "organization_campaign_id"})
    )
    samples = samples.merge(keys, on=["organization_campaign_id", "field_id"])
    samples = samples.dropna(subset=["latitude", "longitude"])
 
    field_keys = matches[["campaign_id", "field_id"]].drop_duplicates()
    fields = to_gdf(fields.merge(field_keys, on=["campaign_id", "field_id"]))
 
    n = _base_map()
 
    # Drawn in this order so outlines and points sit on top of the surface
    add_idw_layer(n, samples, fields, "total_carbon_pct", vmin, vmax, name="TC Surface")
    _add_soils(n, SSURGO, [fields], show=show_soils)
    _add_border(n, fields, "Border", style)
    _add_points(n, _prep_points(samples, "total_carbon_pct"), "total_carbon_pct",
                Normalize(vmin=vmin, vmax=vmax), "TC Points", label, style, show_points)
 
    return _finish(n, [fields])
 
 
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
                  cells=250, name="TC Surface", show=True):
    """Interpolated surface as one toggleable layer. Outlines are added
    separately (_add_border) so they get their own toggle."""
    norm = Normalize(vmin=vmin, vmax=vmax)
    pts = _prep_points(samples, value_col)
 
    layer = folium.FeatureGroup(name=name, show=show)
    for geom in fields.geometry:
        # Only use samples inside this field so values don't bleed between fields
        inside = pts[pts.within(geom.buffer(1e-5))]
        if inside.empty:
            continue
        z, bounds = _grid_surface(inside, inside[value_col], geom, cells)
        _add_raster(layer, z, bounds, CARBON_CMAP, norm)
    layer.add_to(m)
 
 
# ---------------------------------------------------------------------------
# Map 3: change between two years
# ---------------------------------------------------------------------------
 
def pair_points(pts_a, pts_b, value_col="total_carbon_pct", max_dist_m=15):
    """One-to-one pairs: a point in each year that are each other's nearest
    neighbour and no more than max_dist_m apart (measured in UTM)."""
    if pts_a.empty or pts_b.empty:
        return gpd.GeoDataFrame(columns=["value_a", "value_b", "change", "dist_m"],
                                geometry=[], crs=pts_a.crs)
 
    utm = pts_a.estimate_utm_crs()
    a_m, b_m = pts_a.to_crs(utm), pts_b.to_crs(utm)
    xa = np.column_stack([a_m.geometry.x, a_m.geometry.y])
    xb = np.column_stack([b_m.geometry.x, b_m.geometry.y])
 
    d, j = cKDTree(xb).query(xa)          # nearest B for each A
    _, back = cKDTree(xa).query(xb)       # nearest A for each B
    keep = (back[j] == np.arange(len(xa))) & (d <= max_dist_m)
 
    a, b = pts_a.iloc[keep], pts_b.iloc[j[keep]]
    out = gpd.GeoDataFrame({
        "value_a": a[value_col].astype(float).values,
        "value_b": b[value_col].astype(float).values,
        "dist_m": d[keep],
    }, geometry=a.geometry.values, crs=pts_a.crs)
    out["change"] = out["value_b"] - out["value_a"]
    return out
 
 
def create_change_map(samples_a, samples_b, fields_a, fields_b,
                      value_col="total_carbon_pct", cells=250,
                      SSURGO=None, label_a="Baseline", label_b="Current",
                      pair_dist_m=15, show_soils=False):
    """Map of (year B - year A), clipped to the area sampled in both years.
    Returns (map, lim) as before; lim is the +/- range of the change scale."""
    pts_a = _prep_points(samples_a, value_col)
    pts_b = _prep_points(samples_b, value_col)
    pairs = pair_points(pts_a, pts_b, value_col, pair_dist_m)
 
    # One change piece per overlapping (field A, field B)
    pieces, overlaps = [], []
    for fa in fields_a.geometry:
        for fb in fields_b.geometry:
            overlap = fa.intersection(fb).buffer(0)
            if overlap.is_empty or overlap.area < 1e-9:
                continue
            overlaps.append(overlap)
            in_pairs = pairs[pairs.within(overlap.buffer(1e-5))]
            if len(in_pairs) >= 3:
                # Preferred: interpolate the paired point differences
                diff, bounds = _grid_surface(in_pairs, in_pairs["change"], overlap, cells)
            else:
                # Fallback when locations weren't revisited: difference of surfaces
                in_a = pts_a[pts_a.within(fa.buffer(1e-5))]
                in_b = pts_b[pts_b.within(fb.buffer(1e-5))]
                if in_a.empty or in_b.empty:
                    continue
                za, bounds = _grid_surface(in_a, in_a[value_col], overlap, cells)
                zb, _ = _grid_surface(in_b, in_b[value_col], overlap, cells)
                diff = zb - za
            pieces.append((diff, bounds))
 
    # Symmetric scale so "no change" is always the middle color
    finite = [np.nanmax(np.abs(d)) for d, _ in pieces if np.isfinite(d).any()]
    lim = max(finite, default=0) or 0.1
    norm = Normalize(vmin=-lim, vmax=lim)
 
    m = _base_map()
 
    layer = folium.FeatureGroup(name="TC Change Surface", show=True)
    for diff, bounds in pieces:
        _add_raster(layer, diff, bounds, CHANGE_CMAP, norm)
    layer.add_to(m)
 
    _add_soils(m, SSURGO, [fields_a, fields_b], show=show_soils)
    _add_border(m, fields_a, f"Border {label_a}", STYLE_A)
    _add_border(m, fields_b, f"Border {label_b}", STYLE_B)
    if overlaps:
        folium.GeoJson(
            gpd.GeoDataFrame(geometry=[unary_union(overlaps)], crs=fields_b.crs),
            name="Overlap Area (compared)", show=False,
            style_function=lambda _: {"color": "#ffd400", "weight": 2,
                                      "fillColor": "#ffd400", "fillOpacity": 0.15},
        ).add_to(m)
 
    return _finish(m, [fields_a, fields_b]), lim
 
 
def legend_html(vmin, vmax, colors=CARBON_COLORS, caption="Total Carbon (%)", n_ticks=5):
    gradient = ", ".join(colors)
    labels = "".join(f"<span>{t:.1f}</span>" for t in np.linspace(vmin, vmax, n_ticks))
    return f"""
<div style="font-family:sans-serif; font-size:13px; max-width:500px; margin:4px 0 16px 0;">
  <div style="height:12px; background:linear-gradient(to right, {gradient}); border:1px solid #999;"></div>
  <div style="display:flex; justify-content:space-between;">{labels}</div>
  <div style="text-align:center;">{caption}</div>
</div>"""