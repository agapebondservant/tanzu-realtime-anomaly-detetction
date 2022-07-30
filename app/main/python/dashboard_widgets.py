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
def show_trends(timeframe):
    try:
        logging.info('Showing trends in Dashboard...')
        fig = main.anomaly_detection_training_pipeline(csv_data_source, '10min', timeframe)
        st.pyplot(fig)
        logging.info('Trend dashboard rendered.')
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


#############################
# Train Sentiment Analysis model
#############################
def train_sentiment_model():
    try:
        logging.info('Training sentiment analysis model...')
        main.sentiment_analysis_training_pipeline(csv_data_source)
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()

#############################
# Perform Sentiment Analysis
#############################


def show_sentiment(text):
    return main.sentiment_analysis_inference_pipeline(text)


#############################
# Render Anomaly Detection Dashboard
#############################
def render_anomaly_detection_dashboard(timeframe):
    try:
        logging.info('Start rendering dashboard widgets...')
        show_trends(timeframe)
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


#############################
# Render Sentiment Analysis Dashboard
#############################
def render_sentiment_analysis_dashboard():
    try:
        logging.info('Start sentiment analysis training...')
        train_sentiment_model()
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()
