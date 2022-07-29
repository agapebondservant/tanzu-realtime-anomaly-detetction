
import joblib
import logging


########################
# Save artifact
# TODO: Use S3-compatible store
########################
def save_artifact(artifact, artifact_name):
    artifact_handle = open(f"artifacts/{artifact_name}.pkl", "wb")
    joblib.dump(artifact, artifact_handle)
    artifact_handle.close()


########################
# Load artifact
# TODO: Use S3-compatible store
########################
def load_artifact(artifact_name):
    artifact_handle = open(f"artifacts/{artifact_name}.pkl", "rb")
    artifact = joblib.load(artifact_handle)
    return artifact


