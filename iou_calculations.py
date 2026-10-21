import pandas as pd
from shapely.geometry import Polygon
import geopandas as gpd
from shapely import wkt
import numpy as np
import shapely


# iou calculation function

def iou_calc(camp_fields):

    # print(camp_fields)
    # making the pandas series into a type of wkt
    camp_fields["geometry"] = camp_fields["geometry_wkt"].apply(wkt.loads)
    ############### test print
    # print(type(camp_fields['geometry_wkt']))
    # print(camp_fields['geometry_wkt'])
    ###############

    # geopandas df
    gdf = gpd.GeoDataFrame(camp_fields, geometry=camp_fields['geometry'], crs="EPSG:4326",)

    ################ testing calculations 
    # gdf["is_valid"] = gdf.is_valid
    # # using "EPSG:32618" becuase it needs to be in a square degree so that the area is can be computed correctly
    # gdf["acres_computed"] = gdf.to_crs("EPSG:32618").area/4046.8564224
    # print(gdf)
    ################

    # columns that will be combined

    cols = ['field_id', 'field_name', 'campaign_name', 'geometry']

    # getting the campaign ids in order of year (most recent first)
    # TODO change so more than two campaigns can be utilized. This can be done with a for loop
    campaign_ids = (gdf[["campaign_id", "year"]].drop_duplicates().sort_values('year', ascending=False)['campaign_id'].tolist())

    # print(campaign_ids)

    # group by the columns that were specified
    by_campaign = {cid: g[cols] for cid, g in gdf.groupby('campaign_id')}

    # the two data frames breaking up into the two campaigns
    recent_fields = by_campaign[campaign_ids[0]]
    historical_fields = by_campaign[campaign_ids[1]]

    # spatial join on inner, both dfs; retain only left_df geometry column
    pairs = gpd.sjoin(recent_fields, historical_fields, how='inner', predicate="intersects", lsuffix="1", rsuffix="2")

    # line up the pairs
    g1 = np.asarray(pairs.geometry.values)
    g2 = np.asarray(historical_fields.geometry.loc[pairs["index_2"]].values)


    # union the pairs
    union = shapely.union(g1, g2)
    # intersect the pairs
    overlap = shapely.intersection(g1, g2)

    pairs["geometry"] = union
    # calcualted acres that union
    pairs["acres_union"] = shapely.area(union) / 4046.8564224
    # calcualted acres that overlap/intersect
    pairs["acres_overlap"] = shapely.area(overlap) / 4046.8564224
    # the calculated iou
    pairs["iou"] = pairs["acres_overlap"] / pairs["acres_union"]
    # drop the duplicate union values
    pairs = pairs.drop(columns=["index_2","geometry", "acres_union", "acres_overlap"]).reset_index(drop=True)

    # print(pairs)
    pairs.insert(2, 'Relationship', "")
    pairs.insert(0, 'Ignore', "")
    pairs.insert(3, 'campaign_id_1', campaign_ids[0])
    pairs.insert(5, 'campaign_id_2', campaign_ids[1])
    # print(pairs)
    pairs_table = pairs

    return pairs_table


