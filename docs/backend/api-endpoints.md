
# 📚 Volumania Backend API

This document describes the REST API for the `volumania-backend`. 
All endpoints are secured with JWT tokens generated from a Kubernetes Bearer token.

---

## 🔐 Authentication

All endpoints (except `/login` and `/health`) require an `Authorization` header:

```
Authorization: Bearer <jwt>
```

You obtain the JWT via:

### POST `/login`

Generates a JWT based on a Kubernetes Bearer token.

#### Example Request

```http
POST /login
Authorization: Bearer <k8s-token>
```

#### Example Response

```json
{
  "access_token": "<jwt>"
}
```

---

## 📦 PVCs

### GET `/pvcs`
Lists all PersistentVolumeClaims (PVCs) visible to the current user based on their Kubernetes token.

#### Example Response

```json
[
  {
    "namespace": "default",
    "name": "data-pvc",
    "size": "5Gi",
    "status": "Bound"
  }
]
```

---

### GET `/pvcs/usage`
Lists PVCs including current usage statistics.

#### Example Response

```json
[
  {
    "namespace": "default",
    "name": "data-pvc",
    "size": "5Gi",
    "used": "3.2Gi",
    "usage_percent": 64.0
  }
]
```

---

### POST `/manualresize`
Performs a manual resize of a PVC.

#### Example Body

```json
{
  "namespace": "default",
  "pvc_name": "data-pvc",
  "new_size": "10Gi"
}
```

#### Example Response

```json
{
  "status": "success",
  "message": "data-pvc resized to 10Gi"
}
```

---

## ⚙️ Autoscaler

### GET `/autoscalers`
Lists all `pvcautoscalers` visible to the user.

#### Example Response

```json
[
  {
    "name": "example-autoscaler",
    "namespace": "default",
    "pvcName": "data-pvc",
    "stepSize": "2Gi",
    "maxSize": "20Gi",
    "threshold": 75,
    "cooldown": 300
  }
]
```

---

### POST `/autoscalers`
Creates a new autoscaler.

#### Example Body

```json
{
  "namespace": "default",
  "pvcName": "data-pvc",
  "stepSize": "2Gi",
  "maxSize": "20Gi",
  "threshold": 75,
  "cooldown": 300
}
```

---

### PUT `/autoscalers/{name}`
Updates an existing autoscaler.

#### Example Body

```json
{
  "stepSize": "4Gi",
  "maxSize": "40Gi",
  "threshold": 80,
  "cooldown": 600
}
```

---

### DELETE `/autoscalers/{name}`
Deletes an autoscaler.

#### Example Response

```json
{
  "status": "deleted",
  "name": "example-autoscaler"
}
```

---

## 🔍 Additional Endpoints

### GET `/health`
Simple health check endpoint for load balancers or uptime checks.

#### Example Response
```json
{
  "status": "ok"
}
```

---

✅ You can place this file as `docs/api.md` in your repository and link to it from your `README.md`:

```markdown
[📚 API Documentation](docs/api.md)
```
