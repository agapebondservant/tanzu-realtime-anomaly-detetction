import joblib
import logging
import numpy as np
import pandas as pd
import feature_store
from datetime import datetime, timedelta


def get_data(data=None, last_offset=None):
    print()