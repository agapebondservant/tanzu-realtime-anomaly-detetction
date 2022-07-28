########################
# Imports
########################
import pandas as pd
import numpy as np
import warnings
import traceback
from pylab import rcParams
from app.main.python import sentiment_analysis

########################
# Set-up
########################
warnings.filterwarnings('ignore')
rcParams['figure.figsize'] = (15, 6)


#############################
# Sentiment Analysis Pipeline
#############################
def sentiment_analysis_training_pipeline(source):
    print("Starting Sentiment Analysis Pipeline.......................")

    try:
        # Ingest Data
        df = sentiment_analysis.ingest_data(source)

        # Prepare Data
        df = sentiment_analysis.sentiment_prepare_data(df)

        # Perform Test-Train Split
        df_train, df_test = sentiment_analysis.sentiment_train_test_split(df)

        # Perform tf-idf vectorization
        x_train, x_test, y_train, y_test, vectorizer = sentiment_analysis.sentiment_vectorization(df_train, df_test)

        # Generate model
        model = sentiment_analysis.sentiment_train(x_train, x_test, y_train, y_test)

        # Store metrics
        sentiment_analysis.sentiment_generate_and_save_metrics(x_train, x_test, y_train, y_test, model)

        # Save model
        sentiment_analysis.sentiment_save_model(model)

        # Save vectorizer
        sentiment_analysis.sentiment_save_vectorizer(vectorizer)

        print("Sentiment Analysis Pipeline execution complete.")
    except Exception as e:
        print('Could not complete execution - error occurred: ')
        traceback.print_exc()


def sentiment_analysis_inference_pipeline(text):
    return sentiment_analysis.sentiment_predict(text)
