
# Volumania – Kubernetes volumes on autopilot

**Volumania** is a Kubernetes operator that automatically resizes PersistentVolumeClaims (PVCs) based on their usage.  
It supports both **manual resizing via CRDs** and **automatic scaling by directly querying Kubernetes node metrics**.

---

## ✨ Features

- 🔧 Manual PVC resizing via `PVCManualResize` CRD  
- 🚀 Automated PVC scaling with thresholds, step sizes and max sizes  
- 🧩 No Prometheus required – directly uses the Kubernetes kubelet metrics API  
- 🔒 Supports private container registries via `imagePullSecrets`

---

## 📦 Installation

### 1. Add the Helm repository

```bash
helm repo add volumania https://therealpoys.github.io/volumania
helm repo update
```

### 2. Install the Helm chart

```bash
helm install volumania volumania/volumania   --namespace volumania --create-namespace
```

---

## ⚙️ Configuration

You can configure Volumania via the Helm `values.yaml`.

Example:

```yaml
replicaCount: 1

image:
  repository: ghcr.io/therealpoys/volumania
  tag: 0.1.0
  pullPolicy: IfNotPresent

imagePullSecret: regcred  # Optional for private images

resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 50m
    memory: 64Mi
kubernetes:
  serviceHost: kubernetes.default.svc
```

To install with your custom values:

```bash
helm install volumania volumania/volumania -f my-values.yaml
```

---

## 🧾 CRD Examples

### Manual PVC Resize

```yaml
apiVersion: scaling.volumania.io/v1
kind: PVCManualResize
metadata:
  name: resize-my-pvc
spec:
  pvcName: my-pvc
  newSize: 20Gi
```

### PVC AutoScaler

```yaml
apiVersion: scaling.volumania.io/v1
kind: PVCAutoScaler
metadata:
  name: my-autoscaler
spec:
  pvcName: my-pvc
  minSize: 1Gi
  stepSize: 2Gi
  maxSize: 50Gi
  triggerAbovePercent: 60     # Start scaling if usage exceeds 60%
  checkIntervalSeconds: 30    # Check every 30 seconds
  cooldownSeconds: 60         # Wait at least 60 seconds between resizes
```

---

## 🧪 Development

To run the operator locally inside a cluster (via your ServiceAccount token):

```bash
export KUBERNETES_SERVICE_HOST=kubernetes.default.svc
kopf run --standalone --all-namespaces controllers/main.py
```

---

## 📄 License

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
