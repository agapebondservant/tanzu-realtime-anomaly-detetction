def get_current_datetime():
    return pytz.utc.localize(datetime.now())