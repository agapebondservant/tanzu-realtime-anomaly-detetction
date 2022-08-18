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
from app.main.python import main
import time
import threading
from streamlit.scriptrunner.script_run_context import get_script_run_ctx, add_script_run_ctx

# Initializations
main.initialize()
st.set_option('deprecation.showPyplotGlobalUse', False)
st.session_state.dashboard_global_event = threading.Event()


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
.blinking {
  animation: blinker 1s linear infinite;
  background: url('https://github.com/agapebondservant/tanzu-realtime-anomaly-detetction/blob/main/app/assets/clock.png?raw=true') no-repeat right;
}

@keyframes blinker {
  50% {
    opacity: 0;
  }
}
</style>
""", unsafe_allow_html=True)

st.header('Tanzu/Vmware Realtime Anomaly Detection Demo')

st.text('Near-realtime showcase of sentiment-based anomaly detection using Vmware RabbitMQ')

placeholder_tab1, placeholder_tab2, placeholder_tab3 = st.empty(), st.empty(), st.empty()

tab1, tab2, tab3 = placeholder.tabs(["Home", "Feedback", "Anomalies"])

while True:
    # Charts
    with tab1:
        placeholder_tab1 = st.empty()
        with placeholder_tab1.container():
            logging.info("Refreshing dashboard...")

            timeframe = st.selectbox(
                'Select time period', ('day', 'hour', 'week'), key=f"select_time{time.time()}1")
            st.markdown("<div class='blinking'>&nbsp;</div>", unsafe_allow_html=True)

            dashboard_widgets.render_trends_dashboard(timeframe)

    # Posts
    with tab2:
        placeholder_tab2 = st.empty()
        with placeholder_tab2.container():

            sentiment = 'neutral'
            sentiment_mappings = {'positive': 'color:green', 'negative': 'color:red', 'neutral': 'visibility:hidden'}

            st.write("Enter your thoughts:")
            post = st.text_input('Feedback', '''''', key=f"text_post{time.time()}1")

            if len(post) != 0:
                sentiment = dashboard_widgets.show_sentiment(post)
                st.markdown(
                    f"Sentiment:<br/><span style=font-size:1.6em;{sentiment_mappings[sentiment]}>{sentiment}</span>",
                    unsafe_allow_html=True)

            dashboard_widgets.render_sentiment_analysis_dashboard()

    # Anomalies
    with tab3:
        placeholder_tab3 = st.empty()
        with placeholder_tab3.container():

            timeframe2 = st.selectbox(
                'Select a time period', ('day', 'hour', 'week'), key=f"select_time{time.time()}2")
            st.markdown("<div class='blinking'>&nbsp;</div>", unsafe_allow_html=True)

            dashboard_widgets.render_anomaly_detection_dashboard(timeframe2)

    # time.sleep(15)
    st.session_state.dashboard_global_event.wait(15)
    placeholder_tab1.empty()
    placeholder_tab2.empty()
    placeholder_tab3.empty()




