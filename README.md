### DEPLOYING ANOMALY DETECTION WORKSHOP

NOTE:
* Currently requires **cluster-admin** privileges to set up.
* Assumes that a Learning Center Portal already exists.

#### Contents
1. [Prepare environment](#prepare-env)
2. [Deploy Postgres Instance](#deploy-anomaly-postgres)
3. [Run Methods](#run-methods)

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

#### Deploy Postgres Instance <a name="deploy-anomaly-postgres"/>
* Deploy Postgres cluster:
``` 
kubectl apply -f resources/postgres/postgres.yaml -n rt-analytics
```

* Import data:
```

```

#### Run Methods
* Run methods in a pipeline:

```
python -c "from app.main.python import airline_analytics; airline_analytics.ingest_data('test')"
```
# tanzu-realtime-anomaly-detetction
