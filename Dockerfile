FROM python:3.12-slim

WORKDIR /app

COPY controllers/ /app/controllers
COPY requirements.txt /app/requirements.txt 

RUN pip install --no-cache-dir -r requirements.txt

ENV PROMETHEUS_URL=http://prometheus-kube-prometheus-prometheus.monitoring.svc:9090

CMD ["kopf", "run", "--standalone", "--all-namespaces", "controllers/main.py"]
