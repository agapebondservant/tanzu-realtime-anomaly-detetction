kubectl create secret docker-registry image-pull-secret --namespace=default \
  --docker-username=${DATA_E2E_REGISTRY_USERNAME} --docker-password=${DATA_E2E_REGISTRY_PASSWORD} \
  --dry-run -o yaml | kubectl apply -f -