import streamlit as st
import pandas as pd
import numpy as np
import logging
import warnings
import traceback
from pylab import rcParams
from app.main.python import dashboard_widgets
import mpld3
import streamlit.components.v1 as components
import time

st.write("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nanum Gothic');
html, body, [class*="css"]{
   font-family: 'Nanum Gothic';
}
#anomaly-tracking-app{
   color: #6a6161;
}
/*table {
    border-collapse: collapse;
    margin: 25px 0;
    font-size: 0.9em;
    font-family: sans-serif;
    min-width: 400px;
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
}
table thead tr {
    background-color: #009879;
    color: #ffffff;
    text-align: left;
}
th, td {
    padding: 12px 15px;
}
tbody tr {
    border-bottom: 1px solid #dddddd;
}

tbody tr:nth-of-type(even) {
    background-color: #f3f3f3;
}

tbody tr:last-of-type {
    border-bottom: 2px solid #009879;
}
tbody tr.active-row {
    font-weight: bold;
    color: #009879;
}*/
thead th {
    background-color: bisque;
}
</style>
""", unsafe_allow_html=True)

st.header('Anomaly Tracking App')

st.text('Tracks outliers in realtime')

data = []

# Table
# TODO: Consume from queue
df = pd.DataFrame({
        'Messages': data,
        'Time': []
    }
).set_index('Time')

with st.spinner('Checking alerts...'):
    time.sleep(3)
st.table(df)
