import joblib
import logging

########################
# Cache
# TODO: Use distributed backend like Ray/Dask/Gemfire
########################
cache = {}


########################
# Save to cache
########################
def save_artifact(artifact, artifact_name):
    try:
        save_to_cache(artifact, artifact_name)
        save_to_backend(artifact, artifact_name)
    except Exception as e:
        logging.debug('Could not complete execution - error occurred: ', exc_info=True)


########################
# Save to cache
########################
def load_artifact(artifact_name):
    try:
        artifact = load_from_cache(artifact_name)
        if artifact is None:
            artifact = load_from_backend(artifact_name)
        return artifact
    except Exception as e:
        logging.debug('Could not complete execution - error occurred: ', exc_info=True)


########################
# Save artifact
# TODO: Use S3-compatible store
########################
def save_to_backend(artifact, artifact_name):
    try:
        artifact_handle = open(f"app/artifacts/{artifact_name}.pkl", "wb")
        joblib.dump(artifact, artifact_handle)
        artifact_handle.close()
    except Exception as e:
        logging.debug('Could not complete execution - error occurred: ', exc_info=True)


########################
# Load artifact
# TODO: Use S3-compatible store
########################
def load_from_backend(artifact_name):
    artifact = None
    try:
        artifact_handle = open(f"app/artifacts/{artifact_name}.pkl", "rb")
        artifact = joblib.load(artifact_handle)
    except Exception as e:
        logging.debug('Could not complete execution - error occurred: ', exc_info=True)
    finally:
        return artifact


########################
# Save offset
########################
def save_offset(offset, offset_name):
    save_artifact(offset, f'{offset_name}_offset')


########################
# Load offset
########################
def load_offset(offset_name):
    return load_artifact(f'{offset_name}_offset')


########################
# Save to cache
########################
def save_to_cache(artifact, artifact_name):
    cache[artifact_name] = artifact
    # st.session_state[artifact_name] = artifact


########################
# Load offset
# TODO: Use distributed backend like Ray/Dask/Gemfire
########################
def load_from_cache(artifact_name):
    # return st.session_state[artifact_name]
    return cache.get(artifact_name)
