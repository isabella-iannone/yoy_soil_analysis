# Main function for year over year analysis
import sys
import iou_calculations
import map_vis
from streamlit_app_proto import create_app
import os
import load_data
import pandas as pd
import streamlit as st
from shapely.geometry import Polygon
import get_SSURGO_data
from config import MATCHES_PATH

# geojson data
FIELDS_PATH = r'C:\Users\isabe\year_or_year_testing_info\field_polygons_year_or_year_test.csv'

# field data
DATA_PATH = r'C:\Users\isabe\year_or_year_testing_info\field_data_year_or_year_test.csv'


# naming the geojson column
GEOM_COL = "geometry_wkt"

# first streamlit call to setup the app
st.set_page_config(page_title="Year over year field matching", layout="wide")

def file_version(path):
    """Last-modified time of a file, or None if it doesn't exist yet.
    Used as a cache key so cached loaders re-run only when the file changes."""
    return os.path.getmtime(path) if os.path.exists(path) else None

# cache setup
# only re-run when there are changes made
@st.cache_data
def load_inputs(fields_path, data_path, data_version): 
    return load_data.load_all(fields_path, data_path, geom_col=GEOM_COL)

@st.cache_data
def get_pairs(_fields_gdf, data_version):
    return iou_calculations.iou_calc(_fields_gdf)

@st.cache_resource
def get_map(_fields_gdf):
    return map_vis.create_map(_fields_gdf)

@st.cache_data(ttl="30d", show_spinner="Downloading SSURGO soils...")
def get_ssurgo(farm_wkt):
    polys = get_SSURGO_data.get_polygons(farm_wkt)
    horizons = get_SSURGO_data.get_horizons(polys["mukey"].unique())
    return polys, horizons

@st.cache_data
def load_match(match_path, match_version):
    return load_data.load_matches(match_path)


def main():
    print("Main function")

    st.session_state["runs"] = st.session_state.get("runs", 0) + 1
    st.sidebar.write("Script runs:", st.session_state["runs"])

    data_version = (file_version(FIELDS_PATH), file_version(DATA_PATH))

    # load the data once
    fields_gdf, samples_gdf = load_inputs(FIELDS_PATH, DATA_PATH, data_version)
    print(f"{len(fields_gdf)} fields, {len(samples_gdf)} samples loaded")
    st.session_state["samples_gdf"] = samples_gdf
    st.session_state["fields_gdf"] = fields_gdf
    st.sidebar.write("Stored samples:", type(st.session_state.get("samples_gdf")).__name__)


    pairs_table = get_pairs(fields_gdf, data_version)
    # print(pairs_table)
        
    field_map = get_map(fields_gdf)

    farm_wkt = get_SSURGO_data.farm_boundary_wkt(fields_gdf)

    try:
        ssurgo_polys, ssurgo_horizons = get_ssurgo(farm_wkt)
    except get_SSURGO_data.SDAError as e:
        print(f"SSURGO unavailable: {e}")   # terminal only
        ssurgo_polys = ssurgo_horizons = None

    matches = None
    if st.session_state.get("matches_saved"):
        matches = load_match(MATCHES_PATH, file_version(MATCHES_PATH))
 
    # 4. Hand everything the pages need to session state
    # st.session_state["fields_gdf"] = fields_gdf
    # st.session_state["samples_gdf"] = samples_gdf
    st.session_state["farm_wkt"] = farm_wkt
    st.session_state["ssurgo_polys"] = ssurgo_polys
    st.session_state["ssurgo_horizons"] = ssurgo_horizons
    st.session_state["matches"] = matches


    def home():
        create_app(pairs_table, fields_gdf, field_map)

    st.sidebar.write("Flag when building pages:", st.session_state.get("matches_saved"))
    
    pages = [st.Page(home, title="Home", icon="🏠", default=True)]
    if st.session_state.get("matches_saved"):
        # matches = load_match(MATCHES_PATH, data_version)
        pages.append(st.Page("analysis_page.py", title="Analysis", icon="📊"))
        # print("Len pages list", pages)
    # st.sidebar.write("Pages:", [p.title for p in pages])

    pg = st.navigation(pages)
    pg.run()

    # heat_map = map_vis.create_heat_map(matches, farm_wkt, samples_gdf)


if __name__ == "__main__":
    main()

