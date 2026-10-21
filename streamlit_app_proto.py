import streamlit as st
from streamlit_folium import st_folium
import map_vis

# Take in the map that was created in map_vis, pairs of all IOU that are not duplicates, fields list with ID and name together, and data to run analysis on
def create_app(map, pairs_table, camp_fields, camp_data):
    st.write("""
    # DRAFT*""")
    st.title("Year or Year Analysis")
    st.subheader("Map of Campaigns")

    st_data = st_folium(map, use_container_width=True, height=500, width=600)

    # setting what columns can be ignored
    ignore_cols = ["field_id_1", "field_id_2", "campaign_name_1", "campaign_name_2", "campaign_id_1", "campaign_id_2"]
    config = {col: None for col in ignore_cols}
    # number 1 is the campaign that was the most recent 
    # change_headers = {"field_name_1": f"{pairs_table['campaign_name_1'].iloc[0]}", "field_name_2": f"{pairs_table['campaign_name_2'].iloc[0]}", "iou": "IOU"}

    camp_fields["field_label"] = camp_fields["field_name"].astype(str)
    # camp_fields["field_label"] = camp_fields["field_id"].astype(str) + "(#" + camp_fields["field_id"].astype(str) + ")"
    campaign_id_1 = pairs_table['campaign_id_1'].iloc[0]
    campaign_id_2 = pairs_table['campaign_id_2'].iloc[0]
    camp_rows = camp_fields[camp_fields["campaign_id"] == campaign_id_1]
    camp_1_field_options = camp_rows["field_label"].tolist()
    hist_rows = camp_fields[camp_fields["campaign_id"] == campaign_id_2]
    camp_2_field_options = hist_rows["field_label"].tolist()



    #TODO not sure where this functionality should go but if the iou is greater than >.85 than the automatic relationship should be 1:1
    #TODO only have good IOU pre-populate
    #TODO if ignore is selected than clear the second campaign fields from that row


    new_table = st.data_editor(
                    pairs_table,
                    column_config={
                        **config,
                        # **change_headers, 
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


    # once every relationship and each field from each campaign is captured have a save button green in

    


