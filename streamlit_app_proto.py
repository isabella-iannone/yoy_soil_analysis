import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
from config import MATCHES_PATH 
# Take in the map that was created in map_vis, pairs of all IOU that are not duplicates, fields list with ID and name together, and data to run analysis on
def create_app(pairs_table, camp_fields, map):
    st.write("""
    # DRAFT*""")
    st.title("Year or Year Analysis")
    st.subheader("Map of Campaigns")

    # MATCHES_PATH = r'C:\Users\isabe\year_or_year_testing_info\matches.csv'

    st_folium(map, height=500)


    pairs_table = pairs_table.copy()
    pairs_table["field_name_1"] = pairs_table["field_name_1"].astype(str).apply(lambda v: [v])
    pairs_table["field_name_2"] = pairs_table["field_name_2"].astype(str).apply(lambda v: [v])

    # setting what columns can be ignored
    ignore_cols = ["field_id_1", "field_id_2", "campaign_name_1", "campaign_name_2", "campaign_id_1", "campaign_id_2"]
    config = {col: None for col in ignore_cols}
    # number 1 is the campaign that was the most recent 
    change_headers = {"iou": "IOU"}

    camp_fields["field_label"] = camp_fields["field_name"].astype(str)
    # camp_fields["field_label"] = camp_fields["field_id"].astype(str) + "(#" + camp_fields["field_id"].astype(str) + ")"
    campaign_id_1 = pairs_table['campaign_id_1'].iloc[0]
    campaign_id_2 = pairs_table['campaign_id_2'].iloc[0]
    camp_rows = camp_fields[camp_fields["campaign_id"] == campaign_id_1]
    camp_1_field_options = camp_rows["field_label"].tolist()
    hist_rows = camp_fields[camp_fields["campaign_id"] == campaign_id_2]
    camp_2_field_options = hist_rows["field_label"].tolist()

   
    new_table = st.data_editor(
                    pairs_table,
                    column_config={
                        **config,
                        **change_headers, 
                        "Ignore": st.column_config.SelectboxColumn(
                                "Ignore",
                                help="Select fields to ignore",
                                width= "small",
                                options=["Ignore - Historical", "Ignore - New"],
                        ),
                        "Relationship": st.column_config.SelectboxColumn(
                            "Relationship",
                            help="How the fields are related between campaigns",
                            width="small",
                            options=["1:1", "1:*", "*:1", "*:*"],
                            required=True,
                        ),
                        "field_name_1": st.column_config.MultiselectColumn(
                                f"{pairs_table['campaign_name_1'].iloc[0]}",
                                help="Select one or more fields",
                                options=camp_1_field_options,
                                required=True,
                        ),
                        "field_name_2": st.column_config.MultiselectColumn(
                                f"{pairs_table['campaign_name_2'].iloc[0]}",
                                help="Select one or more fields",
                                options=camp_2_field_options,
                                required=True
                        )
                       
                    },
                    # disable the editing of certain columns
                    disabled= ["iou"],
                    hide_index=True,
                )

    ids_1 = dict(zip(camp_rows["field_label"], camp_rows["field_id"]))
    ids_2 = dict(zip(hist_rows["field_label"], hist_rows["field_id"]))

    records = []

    # print("FIELD CHECK:", type(new_table["field_name_1"].iloc[0]), new_table["field_name_1"].iloc[0])

    for group_id, row in new_table.iterrows():
        for campaign_id, names, ids in [(campaign_id_1, row["field_name_1"], ids_1), (campaign_id_2, row["field_name_2"], ids_2)]:
            for name in names or []:
                records.append({"group_id": f"{campaign_id_1}-{campaign_id_2}-{group_id}", "campaign_id": campaign_id, "field_id": ids[name], "relationship": row["Relationship"], "ignore": row["Ignore"]})
    matches = pd.DataFrame(records)
    matches["ignore"] = matches["ignore"].replace("", pd.NA)

    # make sure each field from each campaign is accounted for 

    used = set(matches["field_id"]) if not matches.empty else set()
    missing_1 = camp_rows.loc[~camp_rows["field_id"].isin(used), "field_label"].tolist()
    missing_2 = hist_rows.loc[~hist_rows["field_id"].isin(used), "field_label"].tolist()
    twice = matches[matches.duplicated(["campaign_id", "field_id"])] if not matches.empty else matches

    id_to_label = dict(zip(camp_fields["field_id"], camp_fields["field_label"]))
    campaign_names = dict(zip(camp_fields["campaign_id"], camp_fields["campaign_name"]))

    problems = []
    if missing_1:
        problems.append(f"Not matched in {pairs_table['campaign_name_1'].iloc[0]}: {', '.join(missing_1)}")
    if missing_2:
        problems.append(f"Not matched in {pairs_table['campaign_name_2'].iloc[0]}: {', '.join(missing_2)}")
    if not twice.empty:
        twice_unique = twice.drop_duplicates(["campaign_id", "field_id"])
        twice_names = [f"{id_to_label[fid]} ({campaign_names[cid]})" for cid, fid in zip(twice_unique["campaign_id"], twice_unique["field_id"])]
        problems.append(f"Used in more than one row: {', '.join(twice_names)}") 


    if st.button("Confirm Matches"):
        if problems:
            st.error("Matches not saved. Every field needs to be matched or ignored first")
            for problem in problems:
                st.error(problem)
            st.session_state["matches_saved"] = False
        else:
            matches.to_csv(MATCHES_PATH, index=False)
            st.session_state["matches"] = matches
            st.session_state["matches_saved"] = True
            st.rerun()

    if st.session_state.get("matches_saved"):
        st.success("Matches saved")
        st.page_link("analysis_page.py",
                     label="Year over Year Analysis of Your Campaigns",
                     icon="📊")



    # Table with number of samples taken and acres sampled
        # put in a caveat that this is only looking at the fields that are being included in the yoy analysis

    # Total carbon % heat map ******* need to exclude outliers using the k=3 fence rule




    



