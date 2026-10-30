# second page of app that contains the analysis of campaigns over time 

import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
# from config import MATCHES_PATH
import os
import map_vis
import streamlit.components.v1 as components
import geopandas as gpd


# def load_matches():
#     matches = st.session_state.get("matches")
#     if matches is None and os.path.exists(MATCHES_PATH):
#         matches = pd.read_csv(MATCHES_PATH)
#     return matches


st.title("Year Over Year Analysis")

# dropping the ignored fields
# def rid_ignore(matches):
#     match_fields = matches[matches["ignore"].isnull()]
#     print(match_fields)
#     return match_fields


def summary_table(matches, fields_gdf, samples_gdf):
    # only the campaign ids that are in the matches are going to be included
    # need to count the samples taken from the fields and the depth that was specified

    
    
    matched_fields = fields_gdf.merge(matches[["campaign_id", "field_id"]].drop_duplicates(),
                                      on=["campaign_id", "field_id"], how="inner",)
    # need to count only the samples that are 0-15 cm and not all the samples

    print(matched_fields)
    print(samples_gdf)
    # dropping the geo column to covert it to a pandas dataframe instead of a geodataframe
    matched_fields = matched_fields.drop(columns=["geometry_geojson", "geometry"])
    samples_gdf = samples_gdf.drop(columns=["geometry"])
    # matched_fields = matched_fields.drop(matched_fields[["geometry_geojson", "geometry"]])
    # 
    print("This is the type of matched fields", type(matched_fields))

    campaign_ids = sorted(matches["campaign_id"].unique())
    totals = {}

    #TODO when 30 is an option change this value
    spec_depth = 15

    # loop through the samples and if they are in the campaign and depth add to the summary
    for id in campaign_ids:
        camp_samples = samples_gdf[samples_gdf["organization_campaign_id"] == id]
        spec_depth_samples = camp_samples[camp_samples["sample_depth"] == spec_depth]
        totals[id] = {
            # TODO when SQL is defined correctly have campaign name in the csv to pull from
            "Campaign Name": id,
            "Number of Samples": spec_depth_samples["total_carbon_pct"].count(),
            "Number of Fields": spec_depth_samples["field_id"].nunique(),
            "Number of Acres": spec_depth_samples["acres"].sum(),
        }
    #TODO need to see how this working
    totals_df = pd.DataFrame.from_dict(totals, orient="index")

    totals_df.index.name = "campaign_id"
    totals_df = totals_df.reset_index()

    sum_cols = ["Number of Samples", "Number of Fields", "Number of Acres"]

    total_row = totals_df[sum_cols].sum().to_frame().T
    total_row["campaign_id"] = "Total"

    totals_df = pd.concat([totals_df, total_row], ignore_index=True)
    totals_df["campaign_id"] = totals_df["campaign_id"].astype(str)

    return (totals_df)




def heat_maps(samples_gdf, fields_gdf, matches, ssurgo_polys):
    # Keep only fields that appear in matches (ignored rows are already removed)
    keep = set(zip(matches["campaign_id"].astype(str), matches["field_id"].astype(str)))
    fields_gdf = fields_gdf[
        [(str(c), str(f)) in keep
         for c, f in zip(fields_gdf["campaign_id"], fields_gdf["field_id"])]
    ]
    campaign_ids = sorted(matches["campaign_id"].unique())


    campaign_ids = sorted(matches["campaign_id"].unique())
    names = dict(zip(fields_gdf["campaign_id"], fields_gdf["campaign_name"]))


    vals = samples_gdf["total_carbon_pct"].dropna()
    vmin, vmax = vals.min(), vals.max()

    cols = st.columns(len(campaign_ids)+1)
    for col, cid in zip(cols, campaign_ids):
        with col:
            st.markdown(f"**{names.get(cid, cid)}**")
            print(type(samples_gdf))
            print(samples_gdf)
            m = map_vis.create_heat_map(
                # TODO when SQL query is finalized change this to campaign_id
                samples_gdf[samples_gdf["organization_campaign_id"] == cid],
                fields_gdf[fields_gdf["campaign_id"] == cid],
                matches[matches["campaign_id"] == cid],
                ssurgo_polys,
                vmin,
                vmax,
            )
            st_folium(m, height=450, key=f"heat_map_{cid}", returned_objects=[])

    if len(campaign_ids) >= 2:
        base, latest = campaign_ids[0], campaign_ids[-1]
        with cols[-1]:
            st.markdown(f"**Change: {names.get(base, base)} → {names.get(latest, latest)}**")
            m = map_vis.create_change_map(
                samples_gdf[samples_gdf["organization_campaign_id"] == base],
                samples_gdf[samples_gdf["organization_campaign_id"] == latest],
                fields_gdf[fields_gdf["campaign_id"] == base],
                fields_gdf[fields_gdf["campaign_id"] == latest],
            )
            st_folium(m, height=450, key="change_map", returned_objects=[])
    



matches = st.session_state["matches"]
samples_gdf = st.session_state["samples_gdf"]
fields_gdf = st.session_state["fields_gdf"]
ssurgo_polys = st.session_state["ssurgo_polys"]

if matches is None or matches.empty or samples_gdf is None:
    st.warning("Confirm matches on the Home page first.")
    st.stop()

# st.subheader("Matched Fields, got rid of the ignored")
# rid_ignore(matches)

st.subheader("Summary State of Campaigns for 0-15 cm")
# st.table(summary_table(matches, fields_gdf, samples_gdf))
summary_state = summary_table(matches, fields_gdf, samples_gdf)

new_table = st.data_editor(
                    summary_state,
                    # column_config={
                    #     **config,
                    #     **change_headers, 
                    #     "Ignore": st.column_config.SelectboxColumn(
                    #             "Ignore",
                    #             help="Select fields to ignore",
                    #             width= "small",
                    #             options=["Ignore - Historical", "Ignore - New"],
                    #     ),
                    #     "Relationship": st.column_config.SelectboxColumn(
                    #         "Relationship",
                    #         help="How the fields are related between campaigns",
                    #         width="small",
                    #         options=["1:1", "1:*", "*:1", "*:*"],
                    #         required=True,
                    #     ),
                    #     "field_name_1": st.column_config.MultiselectColumn(
                    #             f"{pairs_table['campaign_name_1'].iloc[0]}",
                    #             help="Select one or more fields",
                    #             options=camp_1_field_options,
                    #             required=True,
                    #     ),
                    #     "field_name_2": st.column_config.MultiselectColumn(
                    #             f"{pairs_table['campaign_name_2'].iloc[0]}",
                    #             help="Select one or more fields",
                    #             options=camp_2_field_options,
                    #             required=True
                    #     )
                       
                    # },
                    # disable the editing of certain columns
                    # disabled= ["iou"],
                    hide_index=True,
                )


heat_maps(samples_gdf, fields_gdf, matches, ssurgo_polys)




