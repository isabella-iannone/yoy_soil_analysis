import pandas as pd
from shapely.geometry import Polygon
import geopandas as gpd
from shapely import wkt
import numpy as np
import shapely

camp_fields = pd.read_csv(r'C:\Users\isabe\year_or_year_testing_info\field_polygons_year_or_year_test.csv')

list_camp_fields = camp_fields.set_index('campaign_field_id')['field_name'].to_dict()
print(list_camp_fields)

############### test print
# print(type(camp_fields['geometry_wkt']))
# print(camp_fields['geometry_wkt'])
###############

# making the pandas series into a type of wkt
camp_fields["geometry"] = camp_fields["geometry_wkt"].apply(wkt.loads)

# geopandas df
gdf = gpd.GeoDataFrame(camp_fields, geometry=camp_fields['geometry'], crs="EPSG:4326",)

################ testing calculations 
# gdf["is_valid"] = gdf.is_valid
# # using "EPSG:32618" becuase it needs to be in a square degree so that the area is can be computed correctly
# gdf["acres_computed"] = gdf.to_crs("EPSG:32618").area/4046.8564224
# print(gdf)
################

# testing overlay for two fields at the moment
# splitting the df into each campaign
fields_yone = gdf[gdf['campaign_id'] == 1233][['field_id', 'field_name', 'campaign_name', 'geometry']]
fields_ytwo = gdf[gdf['campaign_id'] == 1234][['field_id', 'field_name', 'campaign_name', 'geometry']]

y1 = fields_yone.reset_index(drop=True)
y2 = fields_ytwo.reset_index(drop=True)

# TODO when integrating this for real need to change so the inner is actually the newest campaign. And need to make this hard coded
# find the pairs that overlap between the different campaigns
pairs = gpd.sjoin(y1, y2, how='inner', predicate="intersects", lsuffix="1", rsuffix="2")

# line up the pairs
g1 = np.asarray(pairs.geometry.values)
g2 = np.asarray(pairs.geometry.values)


# union the pairs
union = shapely.union(g1, g2)
overlap = shapely.intersection(g1, g2)

pairs["geometry"] = union
pairs["acres_union"] = shapely.area(union) / 4046.8564224
pairs["acres_overlap"] = shapely.area(overlap) / 4046.8564224
pairs["iou"] = pairs["acres_overlap"] / pairs["acres_union"]

pairs = pairs.drop(columns="index_2").reset_index(drop=True)

print(pairs)

# union_info["acres"] = union_info.area / 4046.8564224
# union_info["status"] = "both years"
# union_info.loc[union_info["field_id_2"].isna(), "status"] = "year 1 only"
# union_info.loc[u["field_id_1"].isna(), "status"] = "year 2 only"

# union_info.groupby("status")["acres"].sum()



# field_yone = gdf['geometry_wkt'][0]
# field_ytwo = gdf['geometry_wkt'][3]
# print(field_yone)
# print(field_ytwo)
# union_test = field_yone.union(field_ytwo)


# union_info = gpd.overlay(field_yone, field_ytwo, how='union')
# intersect_info = gpd.overlay(field_yone, field_ytwo, how='intersect')

# for i in camp_fields['geometry_geojson']:
#     geopandas.overlay(camp_fields[i], camp_fields[i+1], how='union')


