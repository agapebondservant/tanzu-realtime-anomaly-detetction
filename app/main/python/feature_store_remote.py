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
def save_artifact(artifact, artifact_name):
    try:
        save_to_cache(artifact, artifact_name)
        save_to_backend(artifact, artifact_name)
    except Exception as e:
        logging.info(f'Could not complete execution for save_artifact - {artifact_name} - error occurred: ', exc_info=True)


########################
# Save to cache
########################
def load_artifact(artifact_name, reload=True):
    try:
        artifact = load_from_cache(artifact_name)
        if artifact is None or reload:
            artifact = load_from_backend(artifact_name)
        return artifact
    except Exception as e:
        logging.info(f'Could not complete execution for load_artifact - {artifact_name} - error occurred: ', exc_info=True)


########################
# Save artifact
########################
def save_to_backend(artifact, artifact_name):
    try:
        logging.info(f"saving {artifact_name}...{utils.get_parent_run_id()}")
        controller.log_artifact.remote(utils.get_parent_run_id(), artifact, f"{artifact_name}")
    except Exception as e:
        logging.info('Could not complete execution - error occurred: ', exc_info=True)


########################
# Load artifact
########################
def load_from_backend(artifact_name):
    artifact = None
    try:
        run_id = utils.get_parent_run_id()
        if run_id:
            result = controller.load_artifact.remote(run_id,
                                                     artifact_uri=f"runs:/{run_id}/{artifact_name}",
                                                     dst_path="app/artifacts")
            artifact = ray.get(result)
    except Exception as e:
        logging.info('Could not complete execution - error occurred: ', exc_info=True)
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


########################
# Generate metrics
# TODO: Use distributed backend like Ray/Dask/Gemfire
########################
def generate_autolog_metrics(flavor):
    controller.generate_autolog_metrics.remote(flavor)
