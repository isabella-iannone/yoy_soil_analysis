import streamlit as st
from streamlit_folium import st_folium
import map_vis

def create_app(map, pairs_table):
    st.write("""
    # DRAFT*""")
    st.title("Year or Year Analysis")
    st.subheader("Map of Campaigns")

    st_data = st_folium(map, use_container_width=True, height=500, width=600)

    # setting what columns can be ignored
    ignore_cols = ["field_id_1", "field_id_2"]
    config = {col: None for col in ignore_cols}

    # add column with dropdown for ignore that can be selected

    # add column with dropdown for relationship

    #TODO not sure about this function
    # add column that has how it was matched



    # pairs_table['relationship'] = ["1:1", "1:*", "*:1", "*:*"]

    st.dataframe(pairs_table, column_config=config, hide_index=True)
    


