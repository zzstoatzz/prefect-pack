see [this guide](https://docs-3.prefect.io/3.0/deploy/infrastructure-examples/kubernetes#deploy-a-worker-using-helm)

### tldr

```
helm repo add prefect https://prefecthq.github.io/prefect-helm
helm repo update

kubectl create secret generic prefect-api-key \
--namespace=prefect --from-literal=key=your-prefect-cloud-api-key


helm install prefect-worker prefect/prefect-worker \
  --namespace prefect \
  -f values.yaml
```
