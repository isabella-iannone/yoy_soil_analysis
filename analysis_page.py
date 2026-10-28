# second page of app that contains the analysis of campaigns over time 

import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
# from config import MATCHES_PATH
import os
import map_vis
import streamlit.components.v1 as components
# import geopandas as gpd

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


def summary_table(matches, fields_gdf):
    # match_fields = rid_ignore(matches)

    # only the campaign ids that are in the matches are going to be included
    matched_fields = fields_gdf.merge(matches[["campaign_id", "field_id"]].drop_duplicates(),
                                      on=["campaign_id", "field_id"], how="inner",)

    return (matched_fields.groupby(["campaign_id", "campaign_name"]).agg(fields=("field_id", "nunique"), total_acres=("acres_entered", "sum"), total_sampled=("n_pts", "sum")))

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

st.subheader("Summary State of Campaigns")
st.table(summary_table(matches, fields_gdf))

heat_maps(samples_gdf, fields_gdf, matches, ssurgo_polys)




