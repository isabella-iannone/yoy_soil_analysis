# loading all data for the year over year analysis

import geopandas as gpd
import json
import pandas as pd
from shapely.geometry import shape

WGS84 = 4326


def read_fields_csv(path):
    return pd.read_csv(path)

def read_data_csv(path):
    return pd.read_csv(path)

# def read_matches_csv(path):
#     return pd.read_csv(path)

def _parse_geojson(text):
    geom = json.loads(text)
    if geom.get("type") == "Feature":
        geom = geom["geometry"]
    return shape(geom)

def to_gdf(camp_fields, geom_col="geometry_wkt"):
    # convert the fields table (WKT text column) to a GeoDataFrame
    if geom_col not in camp_fields.columns:
        raise KeyError(
            f"No '{geom_col}' column in the fields CSV. "
            f"Columns found: {list(camp_fields.columns)}"
        )
    geoms = gpd.GeoSeries.from_wkt(camp_fields[geom_col], crs=WGS84)
    gdf = gpd.GeoDataFrame(camp_fields.drop(columns=geom_col), geometry=geoms)

    # TODO not sure about this functionality of this
    # Repair self-intersecting polygons so overlap math doesn't fail later
    invalid = ~gdf.is_valid
    if invalid.any():
        gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].make_valid()
    return gdf

def samples_to_gdf(camp_data, lat_col="latitude", lon_col="longitude"):
    return gpd.GeoDataFrame(
        camp_data,
        geometry=gpd.points_from_xy(camp_data[lon_col], camp_data[lat_col]),
        crs=WGS84,
    )
 
def load_all(fields_path, samples_path, geom_col="geometry"):
    """Read both CSVs and return (fields_gdf, samples_gdf)."""
    fields_gdf = to_gdf(read_fields_csv(fields_path), geom_col=geom_col)
    samples_gdf = samples_to_gdf(read_data_csv(samples_path))
    return fields_gdf, samples_gdf

# def load_matches(matches_path):
#     """Reading matches from csv and returning (matches_df)."""
#     matches_pd = read_data_csv(matches_path)
#     return matches_pd