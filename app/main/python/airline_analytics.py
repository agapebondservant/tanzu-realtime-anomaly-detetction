import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import seasonal_decompose
from pylab import rcParams
from datetime import datetime
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, ExponentialSmoothing
from sklearn.metrics import mean_squared_error, mean_absolute_error
from statsmodels.tsa.statespace.tools import diff
from statsmodels.tsa.stattools import acovf, acf, pacf, pacf_yw, pacf_ols
from pandas.plotting import lag_plot
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf, month_plot, quarter_plot
from statsmodels.tsa.stattools import adfuller
from statsmodels.tools.eval_measures import mse, rmse, meanabs, aic, bic
from pmdarima import auto_arima
from prophet import Prophet
from statsmodels.tsa.seasonal import seasonal_decompose
import warnings

########################
# Set-up
########################
warnings.filterwarnings('ignore')
rcParams['figure.figsize'] = (15, 6)


########################
# Ingest Data
########################
def ingest_data(source):
    print('Ingest data...')
    return pd.read_csv(source, index_col="tweet_created")


########################
# Save Model
########################
def save_model(model):
    print('Saving model...')


########################
# Save Plot
########################
def save_plot(plot):
    print('Saving plot...')


########################
# Plot
########################
def plot(data):
    print('Plotting...')


########################
# Train
########################
def train(data):
    print('Training...')


########################
# Predict/Score
########################
def predict(data):
    print('Scoring...')
