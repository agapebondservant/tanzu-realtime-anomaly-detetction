########################
# Imports
########################
import pandas as pd
import numpy as np
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
from prophet import Prophet
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
from sklearn.model_selection import train_test_split
from app.main.python import feature_store


########################
# Ingest Data
########################
def ingest_data(source):
    print('Ingest data...')
    return pd.read_csv(source, index_col="tweet_created")


########################################################################################################################
# ANOMALY DETECTION
########################################################################################################################

########################################################################################################################
# SENTIMENT ANALYSIS
########################################################################################################################


#############################
# Prepare Data
#############################
def sentiment_prepare_data(df):
    print("Preparing data...")
    df = sentiment_feature_extraction(df)
    df = sentiment_feature_encoding(df)
    return df


#############################
# Perform Feature Encoding
#############################
def sentiment_feature_encoding(df):
    print("Performing feature encoding...")
    target_map = {'positive': 1, 'negative': 0, 'neutral': 2}
    df['target'] = df['airline_sentiment'].map(target_map)
    return df


#############################
# Perform Feature Extraction
#############################
def sentiment_feature_extraction(df):
    print("Performing feature extraction...")
    return df[['airline_sentiment', 'text']].copy()


#############################
# Apply Train-Test Split
#############################
def sentiment_train_test_split(df):
    print("Performing train/test data split...")
    df_train, df_test = train_test_split(df)
    return df_train, df_test


#############################
# Apply Data Vectorization
#############################
def sentiment_vectorization(df_train, df_test):
    print("Preparing data vectorization (tf-idf encoding)...")
    vectorizer = TfidfVectorizer(max_features=2000)
    x_train = vectorizer.fit_transform(df_train['text'])
    x_test = vectorizer.transform(df_test['text'])
    y_train = df_train['target']
    y_test = df_test['target']
    return x_train, x_test, y_train, y_test, vectorizer


########################
# Train
########################
def sentiment_train(x_train, x_test, y_train, y_test):
    print("Training data...")
    model = LogisticRegression(max_iter=500)  # TODO: try different values of C, penalty
    model.fit(x_train, y_train)
    sentiment_generate_and_save_metrics(x_train, x_test, y_train, y_test, model)
    return model


########################
# Generate Metrics
########################
def sentiment_generate_and_save_metrics(x_train, x_test, y_train, y_test, model):
    print("Generating metrics...")
    train_acc = model.score(x_train, y_train)
    test_acc = model.score(x_test, y_test)
    train_roc_auc = roc_auc_score(y_train, model.predict_proba(x_train), multi_class='ovo')
    test_roc_auc = roc_auc_score(y_test, model.predict_proba(x_test), multi_class='ovo')
    # TODO: Use MLFlow
    print("Saving metrics...")
    feature_store.save_artifact({'sentiment_train_acc': train_acc,
                                 'sentiment_test_acc': test_acc,
                                 'sentiment_train_roc_auc': train_roc_auc,
                                 'sentiment_test_roc_auc': test_roc_auc}, 'sentiment_analysis_metrics')


########################
# Save Model
########################
def sentiment_save_model(model):
    print("Saving model...")
    feature_store.save_artifact(model, 'sentiment_analysis_model')


########################
# Save Vectorizer
########################
def sentiment_save_vectorizer(vectorizer):
    print("Saving vectorizer...")
    feature_store.save_artifact(vectorizer, 'sentiment_analysis_vectorizer')


########################
# Predict Sentiment
########################
def sentiment_predict(text):
    print("Predicting sentiment...")
    sample = pd.Series(text)
    vectorizer = feature_store.load_artifact('sentiment_analysis_vectorizer')
    model = feature_store.load_artifact('sentiment_analysis_model')
    transformed_sample = vectorizer.transform(sample)
    classes = ['negative', 'positive', 'neutral']
    return classes[model.predict(transformed_sample)[0]]
