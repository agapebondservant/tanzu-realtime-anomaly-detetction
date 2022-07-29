import streamlit as st
import pandas as pd
import numpy as np
import logging
import warnings
import traceback
from pylab import rcParams
from app.main.python import main

########################
# Set-up
########################
warnings.filterwarnings('ignore')
rcParams['figure.figsize'] = (15, 6)
csv_data_source = 'data/airlinetweets.csv'


#############################
# Show Trends
#############################
def show_trends():
    try:
        logging.info('Showing trends in Dashboard...')
        fig = main.anomaly_detection_training_pipeline(csv_data_source, 'day')
        st.pylot(fig)
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()
