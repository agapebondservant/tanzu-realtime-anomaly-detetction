########################
# Imports
########################
import ray
import os

ray.init(runtime_env={'working_dir': ".", 'pip': "requirements.txt",
                      'env_vars': dict(os.environ),
                      'excludes': ['*.jar', '.git*/', 'jupyter/']}) if not ray.is_initialized() else True
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
import pytz
import warnings
import scipy.stats as st
import math
import seaborn as sns
from pylab import rcParams
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, f1_score, confusion_matrix
import sklearn.model_selection as model_selection
from app.main.python import feature_store, data_source


########################
# Ingest Data
########################
def ingest_data():
    logging.info('Ingest data...')
    return data_source.get_data()


########################################################################################################################
# SENTIMENT ANALYSIS
########################################################################################################################


#############################
# Prepare Data
#############################
def prepare_data(df):
    logging.info("Preparing data...")
    df = feature_extraction(df)
    df = feature_encoding(df)
    return df


#############################
# Perform Feature Encoding
#############################
def feature_encoding(df):
    logging.info("Performing feature encoding...")
    target_map = {'positive': 1, 'negative': 0, 'neutral': 2}
    df['target'] = df['airline_sentiment'].map(target_map)
    return df


#############################
# Perform Feature Extraction
#############################
def feature_extraction(df):
    logging.info("Performing feature extraction...")
    return df[['airline_sentiment', 'text']].copy()


#############################
# Apply Train-Test Split
#############################
def train_test_split(df):
    logging.info("Performing train/test data split...")
    df_train, df_test = model_selection.train_test_split(df)
    return df_train, df_test


#############################
# Apply Data Vectorization
#############################
def vectorization(df_train, df_test):
    logging.info("Preparing data vectorization (tf-idf encoding)...")
    vectorizer = TfidfVectorizer(max_features=2000)
    x_train = vectorizer.fit_transform(df_train['text'])
    x_test = vectorizer.transform(df_test['text'])
    y_train = df_train['target']
    y_test = df_test['target']
    return x_train, x_test, y_train, y_test, vectorizer


########################
# Train
########################
def train(x_train, x_test, y_train, y_test):
    logging.info("Training data...")
    model = LogisticRegression(max_iter=500)  # TODO: try different values of C, penalty
    model.fit(x_train, y_train)
    generate_and_save_metrics(x_train, x_test, y_train, y_test, model)
    return model


########################
# Generate Metrics
########################
def generate_and_save_metrics(x_train, x_test, y_train, y_test, model):
    logging.info("Generating metrics...")
    train_acc = model.score(x_train, y_train)
    test_acc = model.score(x_test, y_test)
    train_roc_auc = roc_auc_score(y_train, model.predict_proba(x_train), multi_class='ovo')
    test_roc_auc = roc_auc_score(y_test, model.predict_proba(x_test), multi_class='ovo')

    logging.info("Saving metrics...")
    feature_store.log_metric(key='sentiment_train_acc', value=train_acc, distributed=False)
    feature_store.log_metric(key='sentiment_test_acc', value=test_acc, distributed=False)
    feature_store.log_metric(key='sentiment_train_roc_auc', value=train_roc_auc, distributed=False)
    feature_store.log_metric(key='sentiment_test_roc_auc', value=test_roc_auc, distributed=False)


########################
# Save Model
########################
def save_model(model):
    logging.info("Saving model...")
    feature_store.save_model(model, 'sentiment_analysis_model')


########################
# Save Vectorizer
########################
def save_vectorizer(vectorizer):
    logging.info("Saving vectorizer...")
    feature_store.save_artifact(vectorizer, 'sentiment_analysis_vectorizer')


########################
# Predict Sentiment
########################
def predict(text):
    logging.info("Predicting sentiment...")
    sample = pd.Series(text)
    vectorizer = feature_store.load_artifact('sentiment_analysis_vectorizer')
    model = feature_store.load_model('sentiment_analysis_model')
    transformed_sample = vectorizer.transform(sample)
    classes = ['negative', 'positive', 'neutral']
    return classes[model.predict(transformed_sample)[0]]
