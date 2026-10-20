# Main function for year over year analysis
import sys
import iou_calculations
import map_vis
import streamlit_app_proto
import os
import pandas as pd
from shapely.geometry import Polygon

#  geojson data
camp_fields = pd.read_csv(r'C:\Users\isabe\year_or_year_testing_info\field_polygons_year_or_year_test.csv')

# field data
camp_data = pd.read_csv(r'C:\Users\isabe\year_or_year_testing_info\field_data_year_or_year_test.csv')


def main():
    print("Main function")
    # Getting the pairs table
    pairs_table = iou_calculations.iou_calc(camp_fields)
    print(pairs_table)
    # creating the map
    map = map_vis.create_map(camp_fields)
    # print(type(map))
    streamlit_app_proto.create_app(map)



    # # # where the map is being saved
    # output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "carbon_map_test.html")
    # map.save(output_path)
    # os.startfile(output_path)

if __name__ == "__main__":
    main()
