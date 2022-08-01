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


#############################
# Show Trends
#############################
def show_trends(timeframe):
    try:
        logging.info('Showing trends in Dashboard...')
        fig = main.anomaly_detection_show_trends('10min', timeframe)
        st.pyplot(fig)
        logging.info('Trend dashboard rendered.')
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()

#############################
# Show Anomalies
#############################


def show_anomalies(timeframe):
    try:
        logging.info('Showing anomalies in Dashboard...')
        fig = main.anomaly_detection_training_pipeline('10min', timeframe, retrain=True)
        st.pyplot(fig)
        logging.info('Anomalies dashboard rendered.')
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


#############################
# Train Sentiment Analysis model
#############################
def train_sentiment_model():
    try:
        logging.info('Training sentiment analysis model...')
        main.sentiment_analysis_training_pipeline()
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()

#############################
# Perform Sentiment Analysis
#############################


def show_sentiment(text):
    return main.sentiment_analysis_inference_pipeline(text)


#############################
# Render Anomaly Dashboard
#############################
def render_anomaly_detection_dashboard(timeframe):
    try:
        logging.info('Start rendering anomaly detection widgets...')
        show_anomalies(timeframe)
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


#############################
# Render Trends Dashboard
#############################
def render_trends_dashboard(timeframe):
    try:
        logging.info('Start rendering trends dashboard widgets...')
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
