########################
# Imports
########################
import pandas as pd
import numpy as np
import logging
from statsmodels.tsa.seasonal import seasonal_decompose
from pylab import rcParams
from datetime import datetime
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, ExponentialSmoothing
from sklearn.metrics import mean_squared_error, mean_absolute_error, median_absolute_error
from statsmodels.tsa.statespace.tools import diff
from statsmodels.tsa.stattools import acovf, acf, pacf, pacf_yw, pacf_ols
from pandas.plotting import lag_plot
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf, month_plot, quarter_plot
from statsmodels.tsa.stattools import adfuller
from statsmodels.tools.eval_measures import mse, rmse, meanabs, aic, bic
from pmdarima import auto_arima
from statsmodels.tsa.seasonal import seasonal_decompose
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from statsmodels.tsa.arima.model import ARIMA
from statistics import median, mean
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
import pytz
import warnings
import scipy.stats as st
import math
import seaborn as sns
from pylab import rcParams
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split
from app.main.python import feature_store


########################################################################################################################
# ANOMALY DETECTION
########################################################################################################################


########################
# Ingest Data
########################
def ingest_data(source):
    logging.info('Ingest data...')
    return pd.read_csv(source, parse_dates=['tweet_created'], index_col=['tweet_created'])


#######################################
# Set Global Values
#######################################
def initialize_input_features(data_freq=10, sliding_window_size=144, total_forecast_window=1440):
    logging.info("Initializing input features...")
    input_features = {
        'data_freq': data_freq,
        'sliding_window_size': sliding_window_size,
        'total_forecast_window': total_forecast_window
    }
    feature_store.save_artifact(input_features, "anomaly_detection_input_features")
    return input_features


#######################################
# Generate and Save EDA Artifacts
#######################################
def generate_and_save_eda_metrics(df):
    logging.info("Generating and saving EDA metrics...")
    data_summary = df.groupby('airline_sentiment').resample('1d').count()[['tweet_id']]
    data_summary = data_summary.unstack(0)
    data_summary['total'] = data_summary.sum(axis=1)
    feature_store.save_artifact(data_summary, "anomaly_detection_eda")
    return data_summary


#######################################
# Perform feature extraction via resampling
#######################################
def extract_features(df, sample_frequency):
    logging.info("Performing feature extraction...")
    scalar = generate_scalars()[1]

    df['sentiment'] = df['airline_sentiment'].map({'positive': 1, 'neutral': 0, 'negative': -1})

    df = standardize_data(scalar, df)

    return save_data_buffers(df, sample_frequency)


#######################################
# Perform Data Standardization
#######################################
def standardize_data(standard_scaler, actual_sentiments):
    logging.info("Performing data standardization...")
    actual_sentiments[['sentiment_normalized']] = \
        standard_scaler.fit_transform(actual_sentiments[['sentiment']])
    return actual_sentiments


#######################################
# Initialize Data Buffers
#######################################
def save_data_buffers(df, sample_frequency):
    logging.info("Generate and save data buffers to use for stream processing...")
    data_buffers = {
        'total_sentiments': df,
        'actual_positive_sentiments': df[df['sentiment'] == 1].resample(f'{sample_frequency}').count(),
        'actual_negative_sentiments': df[df['sentiment'] == -1].resample(f'{sample_frequency}').count(),
        'actual_neutral_sentiments': df[df['sentiment'] == 0].resample(f'{sample_frequency}').count()
    }
    feature_store.save_artifact(data_buffers, 'anomaly_detection_buffers')
    return data_buffers


#######################################
# Generate and Save ADF Results
#######################################
def generate_and_save_adf_results(actual_negative_sentiments):
    logging.info("Generate and save Dickey-Fuller test results...")
    adfuller_results = adfuller(actual_negative_sentiments['sentiment_normalized'])
    feature_store.save_artifact(adfuller_results, 'adf_results')
    return adfuller_results


#######################################
# Check for stationarity
#######################################
def check_stationarity(adfuller_results):
    logging.info("Check for stationarity...")
    return adfuller_results[1] < 0.05


#######################################
# Generate and Save Stationary Results
#######################################
def generate_and_save_stationarity_results(actual_negative_sentiments, sliding_window_size):
    logging.info("Save stationarity plot results...")
    plot_acf(actual_negative_sentiments['sentiment'], lags=20)
    plt.savefig("anomaly_acf.png", bbox_inches='tight')
    plot_pacf(actual_negative_sentiments['sentiment_normalized'])
    plt.savefig("anomaly_pacf.png", bbox_inches='tight')
    seasonal_decompose(actual_negative_sentiments['sentiment'], model='additive', period=sliding_window_size).plot()
    plt.savefig("anomaly_seasonal_decompose.png", bbox_inches='tight')


#######################################
# Plot Positive/Negative Trends
#####################################
def plot_positive_negative_trends(total_sentiments, actual_positive_sentiments, actual_negative_sentiments,
                                  timeframe='day'):
    logging.info("Plotting positive/negative trends...")
    start_date, end_date = total_sentiments['sentiment'].index.max(), total_sentiments['sentiment'].index.max() - timedelta(
        hours= get_time_lags(timeframe))

    fig, ax = plt.subplots(figsize=(12, 5))

    fig.suptitle(f"Trending over the past {timeframe}")
    ax.set_xlim([start_date, end_date])
    ax.plot(actual_positive_sentiments['sentiment'],
            label="Positive Tweets", color="blue")
    ax.plot(actual_negative_sentiments['sentiment'],
            label="Negative Tweets", color="orange")
    ax.hlines(actual_positive_sentiments['sentiment'].median(), xmin=start_date, xmax=end_date, linestyles='--',
              colors='blue')
    ax.hlines(actual_negative_sentiments['sentiment'].median(), xmin=start_date, xmax=end_date, linestyles='--',
              colors='orange')
    ax.set_ylabel('Number of tweets', fontsize=14)
    ax.legend()

    return fig


#######################################
# Perform Auto ARIMA Search
#######################################
def run_auto_arima(actual_negative_sentiments):
    logging.info("Running auto_arima...")
    stepwise_fit = auto_arima(actual_negative_sentiments['sentiment_normalized'], start_p=0, start_q=0, max_p=6,
                              max_q=6,
                              seasonal=False, trace=True)
    feature_store.save_artifact(stepwise_fit, 'anomaly_auto_arima')
    return stepwise_fit


#######################################
# Build ARIMA Model
#######################################
def build_arima_model(sliding_window_size, stepwise_fit, actual_negative_sentiments):
    logging.info(f"Build ARIMA model with params (p,d,q) = {stepwise_fit.order}...")
    actual_negative_sentiments_train = actual_negative_sentiments.iloc[:-int(sliding_window_size)]

    model_arima_order = stepwise_fit.order

    model_arima = ARIMA(actual_negative_sentiments_train['sentiment_normalized'], order=model_arima_order)

    feature_store.save_artifact(model_arima, 'anomaly_arima_model')

    model_arima_results = model_arima.fit()  # fit the model

    feature_store.save_artifact(model_arima_results, 'anomaly_arima_model_results')

    return model_arima_results


#######################################
# Test ARIMA Model
#######################################
def test_arima_model(sliding_window_size, stepwise_fit, actual_negative_sentiments):
    logging.info('Testing ARIMA model...')

    return generate_arima_predictions(sliding_window_size, stepwise_fit, actual_negative_sentiments, pd.Series([]))


#######################################
# Detect Anomalies
#######################################
def detect_anomalies(predictions, sliding_window_size, actual_negative_sentiments):
    logging.info('Detecting anomalies...')

    z_score = st.norm.ppf(.95)  # 95% confidence interval
    mae_scale_factor = 0.67449  # MAE is 0.67449 * std

    predictions = predictions.iloc[-int(sliding_window_size):]

    df_total = actual_negative_sentiments['sentiment_normalized']
    mae = median_absolute_error(df_total.iloc[-int(sliding_window_size):], predictions)

    model_arima_results_full = \
        pd.DataFrame({'fittedvalues': predictions, 'median_values': predictions.rolling(4).median().fillna(0)},
                     index=predictions.index)
    model_arima_results_full['threshold'] = model_arima_results_full['median_values'] + (
            z_score / mae_scale_factor) * mae
    model_arima_results_full['anomaly'] = 0

    model_arima_results_full['actualvalues'] = df_total
    model_arima_results_full['actualvalues'].fillna(0, inplace=True)

    model_arima_results_full.loc[
        model_arima_results_full['actualvalues'] > model_arima_results_full['threshold'], 'anomaly'] = 1
    model_arima_results_full['anomaly'].value_counts()
    return model_arima_results_full


#######################################
# Plot Trend with Anomalies
#######################################
def plot_trend_with_anomalies(model_arima_results_full, sliding_window_size, standard_scalar, stepwise_fit,
                              timeframe='hour'):
    logging.info("Plot trend with anomalies...")
    start_date, end_date = \
        model_arima_results_full.actualvalues.index[-1] - timedelta(hours=get_time_lags(timeframe)), \
        model_arima_results_full.actualvalues.index[-1]

    fitted_values_actual = \
        pd.Series(standard_scalar.inverse_transform(model_arima_results_full.actualvalues),
                  index=model_arima_results_full.actualvalues.index)
    fitted_values_predicted = pd.Series(
        standard_scalar.inverse_transform(model_arima_results_full.fittedvalues),
        index=model_arima_results_full.fittedvalues.index)

    mae_error = median_absolute_error(fitted_values_predicted, fitted_values_actual)
    feature_store.save_artifact(mae_error, 'anomaly_mae_error')

    # Plot curves
    fig, ax = plt.subplots(figsize=(28, 15))
    fig, ax = plt.subplots()
    ax.set_xlim([start_date, end_date])
    ax.plot(fitted_values_actual, label="Actual", color='blue')
    ax.plot(fitted_values_predicted, color='orange', label=f"ARIMA {stepwise_fit.order} Predictions")
    ax.hlines(median(fitted_values_actual), xmin=start_date, xmax=end_date, linestyles='--',
              colors='blue')
    ax.plot(fitted_values_actual[-int(sliding_window_size):].loc[model_arima_results_full['anomaly'] == 1],
            marker='o', linestyle='None', color='red'
            )
    ax.legend()
    fig.suptitle(f"ARIMA Model (Test): \n Median Absolute Error (MAE): {mae_error}", fontsize=16)


#######################################
# Generate ARIMA Predictions
#######################################
def generate_arima_predictions(sliding_window_size, stepwise_fit, actual_negative_sentiments,
                               predictions=pd.Series(dtype='float64')):
    logging.info("Generate ARIMA predictions...")
    # The dataset to forecast with
    df = actual_negative_sentiments.iloc[:-int(sliding_window_size)]

    # The complete dataset
    df_total = actual_negative_sentiments

    start_date, end_date = df_total.index[len(df)], df_total.index[-1]

    # The number of forecasts per sliding window will be the number of AR lags, as ARIMA can't forecast beyond that
    num_lags = stepwise_fit.order[0]

    # The number of sliding windows will be ( size of the sliding window / num_lags )
    num_sliding_windows = sliding_window_size / num_lags

    # Initialize the start & end indexes
    end_idx = len(df) - num_lags

    for idx in np.arange(num_sliding_windows):
        # Compute the start & end indexes
        end_idx = end_idx + num_lags
        start_idx = end_idx - sliding_window_size
        logging.info(f'DEBUG: {start_idx} {end_idx} {end_idx - start_idx} {len(df)} {len(actual_negative_sentiments)}')
        tmp_data = actual_negative_sentiments[int(start_idx):int(end_idx)]
        tmp_arima = ARIMA(tmp_data['sentiment_normalized'], order=stepwise_fit.order)
        tmp_model_arima_results = tmp_arima.fit()
        pred = tmp_model_arima_results.forecast(steps=num_lags, typ="levels").rename('forecasted')
        predictions = predictions.append(pred)

    return predictions


#######################################
# Generate Scalers
#######################################
def generate_scalars():
    logging.info("Generate Standard Scalar references...")
    standard_scaler_positive_sentiment, standard_scaler_negative_sentiment, standard_scaler_neutral_sentiment = \
        StandardScaler(), StandardScaler(), StandardScaler()
    feature_store.save_artifact(standard_scaler_positive_sentiment, 'anomaly_positive_standard_scalar')
    feature_store.save_artifact(standard_scaler_negative_sentiment, 'anomaly_negative_standard_scalar')
    feature_store.save_artifact(standard_scaler_neutral_sentiment, 'anomaly_neutral_standard_scalar')
    return standard_scaler_positive_sentiment, standard_scaler_negative_sentiment, standard_scaler_neutral_sentiment


#######################################
# Perform Inverse Standardization
#######################################
def inverse_standardize_data(standard_scaler, transformed_values):
    logging.info("Perform inverse standardization of input data...")
    inverse_transformed_values = pd.Series(
        standard_scaler.inverse_transform(transformed_values),
        index=transformed_values.index)


#######################################
# Convert timeframe flag to number of time lags
#######################################
def get_time_lags(timeframe='day'):
    logging.info(f"Get time lag for {timeframe}...")
    time_lags = {'hour': 1, 'day': 24, 'week': 168}
    return time_lags[timeframe]
