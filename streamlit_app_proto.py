import streamlit as st
from streamlit_folium import st_folium
import map_vis

def create_app(map, pairs_table):
    st.write("""
    # DRAFT*""")
    st.title("Year or Year Analysis")
    st.subheader("Map of Campaigns")

    st_data = st_folium(map, use_container_width=True, height=500)
    


