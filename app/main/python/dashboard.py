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


def show_sentiment(newpost):
    print(newpost)


st.write("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nanum Gothic');
html, body, [class*="css"]{
   font-family: 'Nanum Gothic';
}
#tanzu-realtime-anomaly-detection-demo{
   color: #6a6161;
}
</style>
""", unsafe_allow_html=True)

st.header('Tanzu/Vmware Realtime Anomaly Detection Demo')

st.text('Near-realtime showcase of sentiment-based anomaly detection using Vmware RabbitMQ')

tab1, tab2, tab3 = st.tabs(["Home", "Feedback", "Anomalies"])

# Charts
with tab1:
    timeframe = st.selectbox(
        'Select time period',
        ('day', 'hour', 'week'))
    dashboard_widgets.render_trends_dashboard(timeframe)

# Posts
with tab2:
    sentiment = 'neutral'
    sentiment_mappings = {'positive': 'color:green', 'negative': 'color:red', 'neutral': 'visibility:hidden'}

    st.write("Enter your thoughts:")
    post = st.text_input('Feedback', '''''')
    placeholder = st.empty()

    if len(post) != 0:
        sentiment = dashboard_widgets.show_sentiment(post)
        placeholder.markdown(f"Sentiment:<br/><span style=font-size:1.6em;{sentiment_mappings[sentiment]}>{sentiment}</span>", unsafe_allow_html=True)

    dashboard_widgets.render_sentiment_analysis_dashboard()

# Anomalies
with tab3:
    timeframe2 = st.selectbox(
        'Select a time period',
        ('day', 'hour', 'week'))
    dashboard_widgets.render_anomaly_detection_dashboard(timeframe2)
