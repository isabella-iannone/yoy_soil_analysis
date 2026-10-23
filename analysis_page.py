# second page of app that contains the analysis of campaigns over time 

import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
from config import MATCHES_PATH
import os

def load_matches():
    matches = st.session_state.get("matches")
    if matches is None and os.path.exists(MATCHES_PATH):
        matches = pd.read_csv(MATCHES_PATH)
    return matches


st.title("Year Over Year Analysis")

# dropping the ignored fields
def rid_ignore(matches):
    match_fields = matches[matches["ignore"].isnull()]
    print(match_fields)
    return match_fields


def summary_table(matches, fields_gdf):
    match_fields = rid_ignore(matches)

    # only the campaign ids that are in the matches are going to be included
    matched_fields = fields_gdf.merge(match_fields[["campaign_id", "field_id"]].drop_duplicates(),
                                      on=["campaign_id", "field_id"], how="inner",)

    return (matched_fields.groupby(["campaign_id", "campaign_name"]).agg(fields=("field_id", "nunique"), total_acres=("acres_entered", "sum"), total_sampled=("n_pts", "sum")))


    # analysis_table = st.dataframe(
    #                     match_fields,
    #                     hide_index=True,
    #                     width='content'

    # )

matches = load_matches()
samples_gdf = st.session_state["samples_gdf"]
fields_gdf = st.session_state["fields_gdf"]

if matches is None or matches.empty or samples_gdf is None:
    st.warning("Confirm matches on the Home page first.")
    st.stop()

# st.subheader("Matched Fields, got rid of the ignored")
# rid_ignore(matches)

st.subheader("Summary State of Campaigns")
st.table(summary_table(matches, fields_gdf))


