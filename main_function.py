# Main function for year over year analysis
import sys
import iou_calculations
import pandas as pd
from shapely.geometry import Polygon

#  geojson data
camp_fields = pd.read_csv(r'C:\Users\isabe\year_or_year_testing_info\field_polygons_year_or_year_test.csv')

# field data
camp_data = pd.read_csv(r'C:\Users\isabe\year_or_year_testing_info\field_data_year_or_year_test.csv')


def main():
    # Write your primary program logic here
    print("Main function")
    pairs_table = iou_calculations.iou_calc(camp_fields)
    print(pairs_table)

if __name__ == "__main__":
    main()
