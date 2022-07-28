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

#############################
# Prepare Data
#############################
def prepare_data(df):
    print("Preparing data...")
    return df


