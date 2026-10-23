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

# geojson data
FIELDS_PATH = r'C:\Users\isabe\year_or_year_testing_info\field_polygons_year_or_year_test.csv'

# field data
DATA_PATH = r'C:\Users\isabe\year_or_year_testing_info\field_data_year_or_year_test.csv'


# naming the geojson column
GEOM_COL = "geometry_wkt"

# first streamlit call to setup the app
st.set_page_config(page_title="Year over year field matching", layout="wide")

# cache setup
# only re-run when there are changes made
@st.cache_data
def load_inputs(fields_path, data_path, data_version): 
    return load_data.load_all(fields_path, data_path, geom_col=GEOM_COL)

@st.cache_data
def get_pairs(_fields_gdf, data_version):
    return iou_calculations.iou_calc(_fields_gdf)

@st.cache_resource
def get_map(_fields_gdf, data_version):
    return map_vis.create_map(_fields_gdf)

@st.cache_data(ttl="30d", show_spinner="Downloading SSURGO soils...")
def get_ssurgo(farm_wkt):
    polys = get_SSURGO_data.get_polygons(farm_wkt)
    horizons = get_SSURGO_data.get_horizons(polys["mukey"].unique())
    return polys, horizons



def main():
    print("Main function")

    data_version = (os.path.getatime(FIELDS_PATH), os.path.getatime(DATA_PATH))

    # load the data once
    fields_gdf, samples_gdf = load_inputs(FIELDS_PATH, DATA_PATH, data_version)
    print(f"{len(fields_gdf)} fields, {len(samples_gdf)} samples loaded")
    st.session_state["samples_gdf"] = samples_gdf
    st.session_state["fields_gdf"] = fields_gdf
    st.sidebar.write("Stored samples:", type(st.session_state.get("samples_gdf")).__name__)


    pairs_table = get_pairs(fields_gdf, data_version)
    # print(pairs_table)
        
    field_map = get_map(fields_gdf, data_version)

    def home():
        create_app(pairs_table, fields_gdf, field_map)

    st.sidebar.write("Flag when building pages:", st.session_state.get("matches_saved"))
    
    pages = [st.Page(home, title="Home", icon="🏠", default=True)]
    if st.session_state.get("matches_saved"):
        pages.append(st.Page("analysis_page.py", title="Analysis", icon="📊"))
        print("Len pages list", pages)
    # st.sidebar.write("Pages:", [p.title for p in pages])

    pg = st.navigation(pages)
    pg.run()

    # streamlit_app_proto.create_app(pairs_table, fields_gdf, field_map)

    farm_wkt = get_SSURGO_data.farm_boundary_wkt(fields_gdf)

    try:
        ssurgo_polys, ssurgo_horizons = get_ssurgo(farm_wkt)
    except get_SSURGO_data.SDAError as e:
        print(f"SSURGO unavailable: {e}")   # terminal only
        ssurgo_polys = ssurgo_horizons = None



if __name__ == "__main__":
    main()


# need a function where it takes in fields_gdf and matches
# get back only the fields that are not ignored
