# DEPLOYING ANOMALY DETECTION WORKSHOP

NOTE:
* Currently requires **cluster-admin** privileges to set up.
* Assumes that a Learning Center Portal already exists.

#### Contents
1. [Prepare environment](#prepare-env)
2. [Install Streamlit](#install-streamlit)
3. [Deploy MLFlow](#deploy-mlflow)
5. [Setup Argo Workflows](#setup-argo-workflows)
6. [Setup Spring Cloud Data Flow Pro version](#setup-scdf-pro)
7. [Setup Jupyterflow](#setup-jupyterflow)
8. [Run Methods](#run-methods)

#### Prepare environment <a name="prepare-env"/>
* Set up namespace and secrets:
```
source .env
kubectl create namespace rt-analytics || true
kubectl create secret docker-registry pivotal-image-pull-secret --namespace=rt-analytics \
  --docker-server=registry.pivotal.io \
  --docker-server=index.docker.io --docker-username="$DATA_E2E_PIVOTAL_REGISTRY_USERNAME" \
  --docker-password="$DATA_E2E_PIVOTAL_REGISTRY_PASSWORD" --dry-run -o yaml | kubectl apply -f -;
kubectl create secret docker-registry image-pull-secret --namespace=rt-analytics \
  --docker-username='${DATA_E2E_REGISTRY_USERNAME}' --docker-password='${DATA_E2E_REGISTRY_PASSWORD}' \
  --dry-run -o yaml | kubectl apply -f -
```
* Deploy Postgres operator (required only if Postgres operator does not already exist):
```
for i in $(kubectl get clusterrole | grep postgres | grep -v postgres-operator-default-cluster-role); \
do kubectl delete clusterrole ${i} > /dev/null 2>&1; done; \
for i in $(kubectl get clusterrolebinding | grep postgres | grep -v postgres-operator-default-cluster-role-binding); \
do kubectl delete clusterrolebinding ${i} > /dev/null 2>&1; done; \
for i in $(kubectl get certificate -n cert-manager | grep postgres); \
do kubectl delete certificate -n cert-manager ${i} > /dev/null 2>&1; done; \
for i in $(kubectl get clusterissuer | grep postgres); do kubectl delete clusterissuer ${i} > /dev/null 2>&1; done; \
for i in $(kubectl get mutatingwebhookconfiguration | grep postgres); \
do kubectl delete mutatingwebhookconfiguration ${i} > /dev/null 2>&1; done; \
for i in $(kubectl get validatingwebhookconfiguration | grep postgres); \
do kubectl delete validatingwebhookconfiguration ${i} > /dev/null 2>&1; done; \
for i in $(kubectl get crd | grep postgres); do kubectl delete crd ${i} > /dev/null 2>&1; done; \
helm install postgres resources/postgres/operatorv1.7.1 -f resources/postgres/overrides.yaml \
    --namespace default --wait; kubectl apply -f resources/postgres/operatorv1.7.1/crds/
```

#### Install Streamlit <a name="prepare-env"/>
* Install Streamlit:
```
python -m ensurepip --upgrade #on mac
sudo apt-get install python3-pip #on ubuntu 
pip3 install pipenv
xcode-select --install #on mac
softwareupdate --install -a #on mac
```

#### Deploy MLFlow <a name="deploy-mlflow"/>
* Deploy MLFlow: see <a href="https://github.com/agapebondservant/mlflow-demo.git" target="_blank>repository</a>

#### Setup Argo Events <a name="setup-argo-workflows"/>
* Setup Argo Events:
```
kubectl create ns argo-events
kubectl apply -f resources/argo/amqp-event-source.yaml -n argo-events

```

#### Setup JupyterFlow <a name="setup-jupyterflow"/>
* Install NFS storage class:
```
helm repo add nfs-ganesha-server-and-external-provisioner https://kubernetes-sigs.github.io/nfs-ganesha-server-and-external-provisioner/
helm install nfs-release nfs-ganesha-server-and-external-provisioner/nfs-server-provisioner -f resources/scdf-pro/nfs-values.yaml
```

* To uninstall NFS (might need to uninstall before reinstalling with new arguments):
```
kubectl delete pvc data-nfs-release-nfs-server-provisioner-0
helm uninstall nfs-release
```

* Setup Jupyterhub Service Account RBAC:
```
kubectl create clusterrolebinding jupyterflow-admin --clusterrole=cluster-admin --serviceaccount=jupyterflow:default
```

* Install Jupyterhub: (**NOTE**: must install the latest version of helm)
```
source .env
helm repo add jupyterhub https://jupyterhub.github.io/helm-chart/
helm repo update
helm upgrade --cleanup-on-fail \
  --install jupyterhub jupyterhub/jupyterhub \
  --namespace jupyterflow \
  --create-namespace \
  --values resources/jupyterhub/jupyterhub-config.yaml
envsubst < resources/jupyterhub/jupyterhub-http-proxy.in.yaml > resources/jupyterhub/jupyterhub-http-proxy.yaml
kubectl apply -f resources/jupyterhub/jupyterhub-http-proxy.yaml -njupyterflow
Navigate to http://$(kubectl get svc proxy-public -njupyterflow -o jsonpath='{.status.loadBalancer.ingress[0].hostname})
Login with username/password: jupyter/jupyter
```

* Install Argo Workflows:
```
kubectl apply -f resources/argo/argo-workflow.yaml -njupyterflow
envsubst < resources/argo/argo-workflow-http-proxy.in.yaml > resources/argo/argo-workflow-http-proxy.yaml
kubectl patch svc argo-server -p '{"spec": {"type": "LoadBalancer"}}' -n jupyterflow
kubectl patch configmap workflow-controller-configmap --patch '{"data":{"containerRuntimeExecutor":"pns"}}' -njupyterflow
kubectl scale deploy argo-server --replicas 0 -njupyterflow && kubectl scale deploy workflow-controller --replicas 0 -njupyterflow
watch kubectl get po -njupyterflow
kubectl scale deploy argo-server --replicas 1 -njupyterflow && kubectl scale deploy workflow-controller --replicas 1 -njupyterflow
watch kubectl get po -njupyterflow
Navigate to https://$(kubectl get svc argo-server -njupyterflow -o jsonpath='{.status.loadBalancer.ingress[0].hostname}):2746
```

* Install Jupyterflow:
```
pip install jupyterflow
```

#### Setup Spring Cloud Data Flow Pro version <a name="setup-scdf-pro"/>
* Install SCDF:
```
source .env
resources/scdf-pro/create-scdf-secret.sh
cd ../tap/
resources/scripts/setup-scdf-1.3.sh
cd -
kubectl apply -f resources/scdf-pro/nfs-pvc.yaml
kubectl apply -f resources/scdf-pro/scdf-service-monitors.yaml -n monitoring-tools
resources/scdf-pro/set_environment_variables.sh
(Navigate to the SCDF dashboard via http://scdf.{YOUR FQDN DOMAIN}/dashboard)
```

* Install Prometheus and Service Monitors (helm install step is only required if prometheus has not already been installed):
```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack --create-namespace --namespace=monitoring-tools \
--set prometheus.service.port=8000 --set prometheus.service.type=ClusterIP \
--set grafana.enabled=false,alertmanager.enabled=false,nodeExporter.enabled=false \
--set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
--set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
--set prometheus.prometheusSpec.shards=0 \
--wait
kubectl apply -f resources/scdf-pro/scdf-pod-monitors.yaml -n monitoring-tools
```

* To **make updates to previously installed SCDF Pro**, make changes to resources/scdf-pro/values.yaml and update:
```
tanzu package installed update scdf-pro-demo \
  --package-name scdfpro.tanzu.vmware.com \
  --version 1.5.0-SNAPSHOT \
  --values-file resources/scdf-pro/values.yaml
```

* Add applications:
- Click "Add Applications" -> "Import application starters from dataflow.spring.io" -> "Stream application starters for RabbitMQ/Docker"
- Click "Import Applications"

#### Run Methods
* Run sentiment analysis training pipeline:
```
python -c "from app.main.python import main; print(main.sentiment_analysis_training_pipeline('data/airlinetweets.csv'))"
```

* Run sentiment analysis inference pipeline:
```
python -c "from app.main.python import main; print(main.sentiment_analysis_inference_pipeline('data/airlinetweets.csv'))"
```

* Run anomaly detection training pipeline:
```
python -c "from app.main.python import main; print(main.anomaly_detection_training_pipeline('data/airlinetweets.csv', 'day'))"
```

* Regenerate pipfile for local use (after updating requirements.txt):
```
pipenv install -r requirements-dev.txt
```

* Launch dashboard locally:
```
pipenv install
pipenv shell
pip install -r requirements-dev.txt
RAY_ADDRESS=<your Ray address> python -m streamlit run app/main/python/ui/dashboard.py --logger.level=info model_name=app.main.python.anomaly_detection_rnn model_type=rnn model_stage=Staging
```

* Launch tracker locally:
```
pipenv install
pipenv shell
pip install -r requirements-dev.txt
python -m streamlit run app/main/python/ui/tracker.py --logger.level=info
```

### Build Docker Containers for Apps
```
docker build -t oawofolu/streamlit .
docker push oawofolu/streamlit
```

### Deploy Apps to Kubernetes
NOTE: Requires RabbitMQ topology (see "Set up RabbitMQ connection"):

* Deploy apps:
```
kubectl create deployment streamlit-dashboard --image=oawofolu/streamlit  -nstreamlit -- streamlit run app/main/python/ui/dashboard.py --model_stage=Production
kubectl create deployment streamlit-dashboard --image=oawofolu/streamlit  -nstreamlit -- streamlit run app/main/python/ui/dashboard.py --model_name=anomaly_arima_model --model_type=arima --model_stage=Staging
kubectl create deployment streamlit-dashboard --image=oawofolu/streamlit  -nstreamlit -- streamlit run app/main/python/ui/dashboard.py --model_name=anomaly_arima_rnn --model_type=rnn --model_stage=Staging
kubectl create deployment streamlit-tracker --image=oawofolu/streamlit  -nstreamlit -- streamlit run app/main/python/ui/tracker.py
kubectl expose deployment streamlit-dashboard --port=8080 --target-port=8501 --name=dashboard-svc --type=LoadBalancer -nstreamlit
kubectl expose deployment streamlit-dashboard --port=8080 --target-port=8501 --name=tracker-svc --type=LoadBalancer -nstreamlit
watch kubectl get all -nstreamlit
# (NOTE: If on AWS, change the timeout settings for the LoadBalancers to 3600)
# (NOTE: Update any associated DNS entries as appropriate)
```

### Set up RabbitMQ connection

* Deploy RabbitMQ topology:
```
git clone git@github.com:agapebondservant/tap-data.git
cd tap-data

kubectl create ns streamlit

kubectl get all -o name -n streamlit | xargs kubectl delete -n streamlit
watch kubectl get all -n streamlit #click Ctrl^C when Ready

kubectl apply -f other/resources/analytics/anomaly-detection-demo/rabbitmq-analytics-cluster.yaml -nstreamlit
watch kubectl get all -n streamlit #click Ctrl^C when Ready

kubectl apply -f other/resources/analytics/anomaly-detection-demo/rabbitmq-analytics-topology.yaml -nstreamlit
watch kubectl get all -n streamlit #click Ctrl^C when Ready

kubectl apply -f other/resources/analytics/anomaly-detection-demo/rabbitmq-analytics-bindings.yaml -nstreamlit
watch kubectl get all -n streamlit #click Ctrl^C when Ready

cd -
```
