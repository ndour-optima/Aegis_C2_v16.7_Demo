import streamlit as st

from aegis.state import get_world, reset_state
from aegis.ui import render_app
from aegis.mission import refresh_mission_layers

st.set_page_config(page_title="Aegis C2 Quantum Dual Use — v16.7", layout="wide")

world = get_world()
init_key = "aegis_v165_initialized"
version_key = "aegis_v165_version"
if st.session_state.get(version_key) != world["meta"]["version"]:
    st.session_state[init_key] = False
    st.session_state[version_key] = world["meta"]["version"]
if not st.session_state.get(init_key, False):
    refresh_mission_layers(world, source="app_load")
    st.session_state[init_key] = True
render_app(world, reset_state)
