kubectl set env deployment/skipper \
  SPRING_CLOUD_SKIPPER_SERVER_PLATFORM_KUBERNETES_ACCOUNTS_DEFAULT_CONFIGMAPREFS=test-ml-model \
  SPRING_CLOUD_SKIPPER_SERVER_PLATFORM_KUBERNETES_ACCOUNTS_DEFAULT_IMAGEPULLSECRET=image-pull-secret \
  SPRING_CLOUD_SKIPPER_SERVER_PLATFORM_KUBERNETES_ACCOUNTS_DEFAULT_REQUESTS_MEMORY=2Gi \
  SPRING_CLOUD_SKIPPER_SERVER_PLATFORM_KUBERNETES_ACCOUNTS_DEFAULT_LIMITS_MEMORY=6Gi
kubectl rollout restart deployment/skipper