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

    print("Matched fields", matched_fields)
    print("Samples", samples_gdf)
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
    if not campaign_ids:
        st.info("No matched fields to map.")
        return
 
    # Keyed by string so IDs match whether they arrive as int or str
    names = {str(c): str(n) for c, n in zip(fields_gdf["campaign_id"], fields_gdf["campaign_name"])}
    label = lambda cid: names.get(str(cid), str(cid))
 
    # One fixed carbon scale for every map
    vals = samples_gdf["total_carbon_pct"].dropna().astype(float)
    vmin, vmax = float(vals.min()), float(vals.max())
 
    base, latest = campaign_ids[0], campaign_ids[-1]
    # TODO when SQL query is finalized change this to campaign_id
    samples_for = lambda cid: samples_gdf[samples_gdf["organization_campaign_id"] == cid]
    fields_for = lambda cid: fields_gdf[fields_gdf["campaign_id"] == cid]
 
    cols = st.columns(len(campaign_ids) + (1 if len(campaign_ids) >= 2 else 0))
 
    for col, cid in zip(cols, campaign_ids):
        with col:
            st.markdown(f"**{label(cid)}**")
            m = map_vis.create_heat_map(
                samples_for(cid),
                fields_for(cid),
                matches[matches["campaign_id"] == cid],
                ssurgo_polys,
                vmin,
                vmax,
                label=label(cid),
                # Baseline is dashed white, every later campaign solid black,
                # matching how they appear on the change map
                style=map_vis.STYLE_A if cid == base else map_vis.STYLE_B,
            )
            st_folium(m, height=450, use_container_width=True, key=f"heat_map_{cid}", returned_objects=[])
            st.markdown(map_vis.legend_html(vmin, vmax), unsafe_allow_html=True)
 
    if len(campaign_ids) >= 2:
        with cols[-1]:
            st.markdown(f"**Change: {label(base)} → {label(latest)}**")
            m, lim = map_vis.create_change_map(
                samples_for(base),
                samples_for(latest),
                fields_for(base),
                fields_for(latest),
                SSURGO=ssurgo_polys,
                label_a=label(base),
                label_b=label(latest),
            )
            st_folium(m, height=450, use_container_width=True, key=f"change_map_{base}_{latest}", returned_objects=[])
            st.markdown(
                map_vis.legend_html(-lim, lim, colors=map_vis.CHANGE_COLORS,
                                    caption="Change in Total Carbon (% points)"),
                unsafe_allow_html=True,
            )

matches = st.session_state["matches"]
samples_gdf = st.session_state["samples_gdf"]
fields_gdf = st.session_state["fields_gdf"]
ssurgo_polys = st.session_state["ssurgo_polys"]

if matches is None or matches.empty or samples_gdf is None:
    st.warning("Confirm matches on the Home page first.")
    st.stop()

# st.subheader("Matched Fields, got rid of the ignored")
# rid_ignore(matches)

st.subheader("Summary Stats of Campaigns for 0-15 cm")
# st.table(summary_table(matches, fields_gdf, samples_gdf))
summary_state = summary_table(matches, fields_gdf, samples_gdf)

new_table = st.data_editor(
                    summary_state,
                    hide_index=True,
                )


heat_maps(samples_gdf, fields_gdf, matches, ssurgo_polys)
# TODO need to change when the drop down for the different depths can be picked
st.caption("Inverse Distance Weighted Interpolation 0-15cm total carbon %", text_alignment="center")
campaign_ids = sorted(matches["campaign_id"].unique())
org_name = samples_gdf["organization"].unique()[0]
st.subheader("Executive Summary Stats")
st.markdown(
    # TODO when the SQL query is updated change this to be campaign names instead of IDs
    f"The contents of this report provides an analysis of total carbon measured across {campaign_ids[0]} and {campaign_ids[1]}. The object of this study is to see how total carbon has changed over (subtract the dates of when these samples were taken)."
    # TODO need to get the number of samples that were taken
    f" {org_name} undertook a soil sampling campaign, collecting soil samples from locations, at depths of 0-15cm, and 15-30cm for total of samples. Samples were tested in a lab for total carbon."
    # TODO need to calculate percentages and averages with total carbon
    f" Results indicate that total soil carbon content ranged from "
    f" Using the Soil Survey Geographic Database (SSURGO) to estimate bulk density on the farm, carbon stocks were calculated for {org_name} [1]."
    # TODO need to get values with averages of C/acre
    f" Carbon stock estimates ranged from "
)


# def shapiro_wilkTest():





