from app.main.python.utils import utils
from app.main.python import anomaly_detection, anomaly_detection_rnn, anomaly_detection_arima

model_name = utils.get_cmd_arg('model_name')
model_type = utils.get_cmd_arg('model_type')
model_stage = utils.get_cmd_arg('model_stage')
anomaly_detection = anomaly_detection.use_model(model_name)
