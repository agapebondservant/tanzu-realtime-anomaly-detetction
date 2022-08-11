import json
from datetime import datetime
import pytz
import pandas as pd
import logging


def dataframe_record_as_json_string(row, date_index, orientation):
    msg = json.loads(row.to_json(orient=orientation))
    msg.insert(0, datetime.strftime(date_index, '%Y-%m-%d %H:%M:%S%z'))
    msg = json.dumps(msg)
    return msg


def get_current_datetime():
    return pytz.utc.localize(datetime.now())


def append_json_list_to_dataframe(df, json_record):
    df2 = pd.DataFrame(
        data={df.columns[col]: json_record[1:][col] for col in range(len(df.columns))},
        index=[json_record[0]])
    return pd.concat([df, df2])


def index_as_datetime(data):
    return pd.to_datetime(data.index, format='%Y-%m-%d %H:%M:%S%z', utc=True)
