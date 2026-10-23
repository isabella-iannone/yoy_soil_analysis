# getting the SSURGO data from the website

# def getSDA(){
    
# }

import requests
import pandas as pd
import geopandas as gpd

SDA = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"

# def sda(q):
#     r = requests.post(SDA, json={"query": q, "format": "JSON+COLUMNNAME"}, timeout=120)
#     rows = r.json()["Table"]
#     return pd.DataFrame(rows[1:], columns=rows[0])

# polys = sda(f"SELECT * FROM SDA_Get_MupolygonWktWgs84_from_Mukey("
#             f"(SELECT STRING_AGG(mukey, ',') FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{farm_wkt}')))")

# def farm_boundary_wkt(fields_gdf, buffer_m=20):
#     shape = fields_gdf.to_crs(5070).union_all().buffer(buffer_m)
#     return gpd.GeoSeries([shape], crs=5070).to_crs(4326).simplify(0.0001).iloc[0].wkt