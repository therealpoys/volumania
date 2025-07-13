# operator/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# Copy code
COPY controllers/ /app/controllers
COPY common/ /app/common
COPY requirements.txt /app/requirements.txt 

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt

ENV KUBERNETES_SERVICE_HOST=kubernetes.default.svc

# Run kopf operator
CMD ["kopf", "run", "--standalone", "--all-namespaces", "controllers/main.py"]
