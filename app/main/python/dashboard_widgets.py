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
from app.main.python import config
from app.main.python.firehose_publisher import FireHosePublisher

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
        sample_freq = '10min'

        # Plot anomalies
        logging.info('Showing anomalies in Dashboard...')
        fig = main.anomaly_detection_training_pipeline(sample_freq, timeframe)
        st.pyplot(fig)

        # Show Stats
        render_stats_dashboard(sample_freq)

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


def render_stats_dashboard(sample_freq):
    try:
        logging.info('Render stats dashboard...')
        stats = None

        with st.spinner('Loading Statistics...'):
            stats = main.anomaly_detection_stats(sample_freq, config.publisher is None)

        if stats is not None:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric('Negative posts in last minute', stats['1min'], delta=f"{stats['1min']}", delta_color="inverse")
            with col2:
                st.metric('Negative posts in last 10 minutes', stats['10min'], delta=f"{stats['10min']}", delta_color="inverse")
            with col3:
                st.metric('Negative posts in last hour', stats['60min'], delta=f"{stats['60min']}", delta_color="inverse")

        logging.info('Anomalies dashboard rendered.')
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()
