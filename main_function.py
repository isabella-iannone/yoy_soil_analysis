# Main function for year over year analysis
import sys
import iou_calculations
# import map_vis
import streamlit_app_proto
import os
import pandas as pd
import streamlit as st
from shapely.geometry import Polygon

#  geojson data
FIELDS_PATH = r'C:\Users\isabe\year_or_year_testing_info\field_polygons_year_or_year_test.csv'

# field data
DATA_PATH = r'C:\Users\isabe\year_or_year_testing_info\field_data_year_or_year_test.csv'


st.set_page_config(page_title="Year over year field matching", layout="wide")

# cache setup
# only re-run when there are changes made
@st.cache_data
def load_data(fields_path, data_path): 
    camp_fields = pd.read_csv(fields_path)
    camp_data = pd.read_csv(data_path)
    return camp_fields, camp_data

@st.cache_data
def get_pairs(camp_fields):
    return iou_calculations.iou_calc(camp_fields)



def main():
    print("Main function")
    # Getting the pairs table

    camp_fields, camp_data = load_data(FIELDS_PATH, DATA_PATH)
    pairs_table = get_pairs(camp_fields)
    print(pairs_table)

    # field_map = map_vis.create_map(camp_fields)

    streamlit_app_proto.create_app(pairs_table, camp_fields, camp_data)


if __name__ == "__main__":
    main()
