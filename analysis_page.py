# second page of app that contains the analysis of campaigns over time 

import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
from config import MATCHES_PATH
import os

# def load_matches():
#     matches = st.session_state.get("matches")
#     if matches is None and os.path.exists(MATCHES_PATH):
#         matches = pd.read_csv(MATCHES_PATH)
#     return matches


st.title("Year Over Year Analysis")



