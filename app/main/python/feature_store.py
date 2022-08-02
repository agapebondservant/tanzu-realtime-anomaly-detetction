
import joblib
import logging
import traceback


########################
# Save artifact
# TODO: Use S3-compatible store
########################
def save_artifact(artifact, artifact_name):
    try:
        artifact_handle = open(f"app/artifacts/{artifact_name}.pkl", "wb")
        joblib.dump(artifact, artifact_handle)
        artifact_handle.close()
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()


########################
# Load artifact
# TODO: Use S3-compatible store
########################
def load_artifact(artifact_name):
    artifact = None
    try:
        artifact_handle = open(f"app/artifacts/{artifact_name}.pkl", "rb")
        artifact = joblib.load(artifact_handle)
    except Exception as e:
        logging.error('Could not complete execution - error occurred: ', exc_info=True)
        traceback.print_exc()
    finally:
        return artifact


