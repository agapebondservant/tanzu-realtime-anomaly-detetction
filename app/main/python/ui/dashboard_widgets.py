import streamlit as st
import logging
import warnings
import traceback
from app.main.python import main, config
import json

########################
# Set-up
########################
warnings.filterwarnings('ignore')


#############################
# Show Trends
#############################
def show_trends(timeframe):
    try:
        with st.spinner('Loading Trends...'):
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
        with st.spinner('Loading Trend with Anomalies...'):
            logging.info('Showing anomalies in Dashboard...')

            if main.anomaly_detection_needs_training():
                main.anomaly_detection_training_pipeline(sample_freq, timeframe, rebuild=True)
            fig = main.anomaly_detection_inference_pipeline(sample_freq, timeframe)
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
        if main.sentiment_analysis_needs_training():
            main.sentiment_analysis_training_pipeline()
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


#############################
# Perform Sentiment Analysis
#############################


def show_sentiment():
    return main.sentiment_analysis_inference_pipeline()


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
            stats = main.anomaly_detection_stats(sample_freq)

        if stats is not None:
            stat = json.loads(stats.iloc[-1].to_json())
            logging.info(f"stat: {stat} {stats}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric('Negative posts in last minute', stat['1min'], delta=f"{stat['1min']}", delta_color="inverse")
            with col2:
                st.metric('Negative posts in last 10 minutes', stat['10min'], delta=f"{stat['10min']}", delta_color="inverse")
            with col3:
                st.metric('Negative posts in last hour', stat['60min'], delta=f"{stat['60min']}", delta_color="inverse")

        logging.info('Anomalies dashboard rendered.')
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()
