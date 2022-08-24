# DEPLOYING ANOMALY DETECTION WORKSHOP

NOTE:
* Currently requires **cluster-admin** privileges to set up.
* Assumes that a Learning Center Portal already exists.

#### Contents
1. [Prepare environment](#prepare-env)
2. [Install Streamlit](#install-streamlit)
3. [Deploy Postgres Instance](#deploy-anomaly-postgres)
4. [Setup Argo Workflows](#setup-argo-workflows)
5. [Setup Jupyterflow](#setup-jupyterflow)
6. [Run Methods](#run-methods)

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

#### Deploy Postgres Instance <a name="deploy-anomaly-postgres"/>
* Deploy Postgres cluster:
``` 
kubectl apply -f resources/postgres/postgres.yaml -n rt-analytics
```

* Import data:
```

```

#### Setup Argo Workflows <a name="setup-argo-workflows"/>
* Setup Argo Workflows:
```
kubectl create ns argo-events
kubectl apply -f resources/argo/amqp-event-source.yaml -n argo-events

```

#### Setup JupyterFlow <a name="setup-jupyterflow"/>
* Install NFS storage class:
```
helm repo add nfs-ganesha-server-and-external-provisioner https://kubernetes-sigs.github.io/nfs-ganesha-server-and-external-provisioner/
helm install my-release nfs-ganesha-server-and-external-provisioner/nfs-server-provisioner
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

* Launch dashboard:
```
pipenv install
pipenv shell
python -m streamlit run app/main/python/dashboard.py --logger.level=info
```

* Launch tracker:
```
pipenv install
pipenv shell
python -m streamlit run app/main/python/tracker.py --logger.level=info
```

### Build Docker Containers for Apps
```
docker build -t oawofolu/streamlit .
docker push oawofolu/streamlit
```

### Deploy Apps to Kubernetes
```
kubectl create ns streamlit
kubectl create deployment streamlit-dashboard --image=oawofolu/streamlit  -nstreamlit -- streamlit run app/main/python/dashboard.py
kubectl create deployment streamlit-tracker --image=oawofolu/streamlit  -nstreamlit -- streamlit run app/main/python/tracker.py
kubectl expose deployment streamlit-dashboard --port=8080 --target-port=8501 --name=dashboard-svc --type=LoadBalancer -nstreamlit
kubectl expose deployment streamlit-dashboard --port=8080 --target-port=8501 --name=tracker-svc --type=LoadBalancer -nstreamlit
watch kubectl get all -nstreamlit
# (NOTE: If on AWS, change the timeout settings for the LoadBalancers to 3600)
# (NOTE: Update any associated DNS entries as appropriate)
```

### Set up RabbitMQ connection
* Update DNS settings for the RabbitMQ service:
