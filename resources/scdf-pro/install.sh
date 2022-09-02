# Install tanzu plugins
tanzu plugin repo update -b tanzu-cli-framework core

tanzu plugin install secret

# Initiate necessaary environment variables
source .env

# Create a secrets namespace
kubectl delete namespace scdf-secrets-ns || true

kubectl create namespace scdf-secrets-ns

# Export target host's docker registry credentials
tanzu secret registry delete scdf-reg-creds-dockerhub --namespace scdf-secrets-ns -y || true

tanzu secret registry add scdf-reg-creds-dockerhub \
  --namespace scdf-secrets-ns \
  --export-to-all-namespaces \
  --server https://index.docker.io/v1/ \
  --username $DATA_E2E_REGISTRY_USERNAME \
  --password $DATA_E2E_REGISTRY_PASSWORD \
  --yes

# Export TanzuNet access credentials
tanzu secret registry delete scdf-reg-creds-dev-registry --namespace scdf-secrets-ns -y || true

tanzu secret registry add scdf-reg-creds-dev-registry \
  --username $DATA_E2E_PIVOTAL_REGISTRY_USERNAME \
  --password $DATA_E2E_PIVOTAL_REGISTRY_PASSWORD \
  --server dev.registry.pivotal.io \
  --namespace scdf-secrets-ns \
  --export-to-all-namespaces \
  --yes

# Deploy the PackageRepository
tanzu package repository add scdf-pro-repo \
  --url dev.registry.pivotal.io/p-scdf-for-kubernetes/scdf-pro-repo:1.5.0-SNAPSHOT

# Deploy the Package
tanzu package install scdf-pro-demo \
  --package-name scdfpro.tanzu.vmware.com \
  --version 1.5.0-SNAPSHOT \
  --values-file resources/scdf-pro/values.yaml

