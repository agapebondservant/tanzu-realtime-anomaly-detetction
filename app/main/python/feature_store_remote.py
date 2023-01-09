import joblib
import logging
from app.main.python.distributed.controllers import ScaledTaskController
import os
from app.main.python.utils import utils
import ray

ray.init(runtime_env={'working_dir': ".", 'pip': "requirements.txt",
                      'env_vars': dict(os.environ),
                      'excludes': ['*.jar', '.git*/', 'jupyter/']}) if not ray.is_initialized() else True

controller = ScaledTaskController.remote()

########################
# Cache
# TODO: Use distributed backend like Ray/Dask/Gemfire
########################
cache = {}


########################
# Save to cache
########################
def save_artifact(artifact, artifact_name, remote=True):
    try:
        save_to_cache(artifact, artifact_name)
        save_to_backend(artifact, artifact_name, remote=remote)
    except Exception as e:
        logging.info(f'Could not complete execution for save_artifact - {artifact_name} - error occurred: ',
                     exc_info=True)


########################
# Save to cache
########################
def load_artifact(artifact_name, remote=True):
    try:
        artifact = load_from_cache(artifact_name)
        if artifact is None or not _get_sync_status(artifact_name):
            artifact = load_from_backend(artifact_name, remote=remote)
        return artifact
    except Exception as e:
        logging.info(f'Could not complete execution for load_artifact - {artifact_name} - error occurred: ',
                     exc_info=True)


########################
# Save artifact
########################
def save_to_backend(artifact, artifact_name, remote=True):
    try:
        logging.info(f"saving {artifact_name} to backend...{utils.get_parent_run_id()}")
        if remote:
            controller.log_artifact.remote(utils.get_parent_run_id(), artifact, f"{artifact_name}")
        else:
            utils.mlflow_log_artifact(utils.get_parent_run_id(), artifact, f"{artifact_name}")
        utils.synchronize(target=_set_out_of_sync, args=(artifact_name,))
    except Exception as e:
        logging.info(f'Could not complete execution for saving {artifact_name} to backend - error occurred: ', exc_info=True)


########################
# Load artifact
########################
def load_from_backend(artifact_name, remote=True):
    artifact = None
    try:
        run_id = utils.get_parent_run_id()
        logging.info(f"Loading {artifact_name} from backend with run id {run_id}...")
        if run_id:
            if remote:
                result = controller.load_artifact.remote(run_id,
                                                         artifact_uri=f"runs:/{run_id}/{artifact_name}",
                                                         dst_path="app/artifacts")
                artifact = ray.get(result)
            else:
                artifact = utils.mlflow_load_artifact(run_id,
                                                      artifact_uri=f"runs:/{run_id}/{artifact_name}",
                                                      dst_path="app/artifacts")
            utils.synchronize(target=_set_in_sync, args=(artifact_name,))
    except Exception as e:
        logging.info(f'Could not complete execution for loading {artifact_name} - error occurred: ', exc_info=True)
    finally:
        return artifact


########################
# Save model
########################
def save_model(model, model_name, flavor='sklearn'):
    try:
        run_id = utils.get_parent_run_id()
        controller.log_model.remote(run_id,
                                    model,
                                    flavor,
                                    artifact_path=flavor,
                                    registered_model_name=model_name,
                                    await_registration_for=None)
    except Exception as e:
        logging.info(f'Could not complete execution for save_model - {model_name}- error occurred: ', exc_info=True)


########################
# Load model
########################
def load_model(model_name, flavor='sklearn', stage='None'):
    try:
        run_id = utils.get_parent_run_id()
        model_uri = f"models:/{model_name}/{stage}"  # if stage else f"runs:/{run_id}/{flavor}"
        result = controller.load_model.remote(run_id,
                                              flavor,
                                              model_uri=model_uri,
                                              dst_path="app/artifacts")
        if result is not None:
            model = ray.get(result)
        else:
            model = load_from_cache(model_name)
        return model
    except Exception as e:
        logging.info(f'Could not complete execution for load_model - {model_name}- error occurred: ', exc_info=True)


########################
# Save offset
########################
def save_offset(offset, offset_name):
    save_artifact(offset, f'{offset_name}_offset')


########################
# Load offset
########################
def load_offset(offset_name, remote=True):
    return load_artifact(f'{offset_name}_offset', remote=remote)


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


########################
# Generate metrics
# TODO: Use distributed backend like Ray/Dask/Gemfire
########################
def generate_autolog_metrics(flavor):
    controller.generate_autolog_metrics.remote(flavor)


########################
# Set in_sync flag=True for this artifact in the cache
# (used to implement dirty read flag for cache)
########################
def _set_in_sync(artifact_name):
    cache[f"{artifact_name}_in_sync_flag"] = True


########################
# Set out_of_sync flag=False for this artifact in the cache
# (used to implement dirty read flag for cache)
########################
def _set_out_of_sync(artifact_name):
    cache[f"{artifact_name}_in_sync_flag"] = False


########################
# Set in-sync status for this artifact in the cache
# (used to implement dirty read flag for cache)
########################
def _get_sync_status(artifact_name):
    cache.get(f"{artifact_name}_in_sync_flag")
