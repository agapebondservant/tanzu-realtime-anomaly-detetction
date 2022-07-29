import streamlit as st
import pandas as pd
import numpy as np
import logging
import warnings
import traceback
from pylab import rcParams
from app.main.python import main
import mpld3
import streamlit.components.v1 as components

########################
# Set-up
########################
warnings.filterwarnings('ignore')
csv_data_source = 'data/airlinetweets.csv'


#############################
# Show Trends
#############################
def show_trends():
    try:
        logging.info('Showing trends in Dashboard...')
        fig = main.anomaly_detection_training_pipeline(csv_data_source, '10min', 'day')
        st.pyplot(fig)
        # fig_html = mpld3.fig_to_html(fig)
        # components.html(fig_html, height=600)
        logging.info('Trend dashboard rendered.')
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


#############################
# Render Dashboard
#############################
def render_dashboard():
    try:
        logging.info('Start rendering dashboard widgets...')
        show_trends()
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


render_dashboard()
