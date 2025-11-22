# Trinity Phase 2 - Deployment Guide

Complete guide for deploying Trinity in various environments.

## Table of Contents

- [Quick Start](#quick-start)
- [Deployment Options](#deployment-options)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Production Best Practices](#production-best-practices)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Docker 20.10+ with Docker Compose
- NVIDIA GPU with Docker GPU support (nvidia-docker2)
- 16GB+ RAM
- 50GB+ disk space

### 1-Minute Deploy

```bash
# Clone repository
git clone https://github.com/Sherin-SEF-AI/Trinity-Phase2.git
cd Trinity-Phase2

# Initialize environment
./scripts/deploy.sh init

# Start services
./scripts/deploy.sh start

# Check status
./scripts/deploy.sh status
```

Access Trinity:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws

---

## Deployment Options

### Option 1: API-Only (Lightweight)

Deploy only the REST API and database.

```bash
./scripts/deploy.sh start api-only
```

**Services**: Database, Redis, Trinity API
**Use Case**: Remote access, headless servers, CI/CD
**Resources**: 4GB RAM, 2 CPU cores

### Option 2: Full Stack (with Monitoring)

Deploy all services including monitoring dashboard.

```bash
./scripts/deploy.sh start full
```

**Services**: Database, Redis, Trinity API, Prometheus, Grafana, pgAdmin
**Use Case**: Production, development, complete observability
**Resources**: 8GB RAM, 4 CPU cores

### Option 3: GUI Mode

Deploy with X11 GUI support.

```bash
# Allow X11 forwarding
xhost +local:docker

# Start with GUI
./scripts/deploy.sh start gui
```

**Services**: Database, Trinity GUI Application
**Use Case**: Desktop usage, local testing
**Resources**: 8GB RAM, GPU required

### Option 4: CARLA Integration

Deploy with CARLA simulator.

```bash
./scripts/deploy.sh start carla
```

**Services**: All services + CARLA Simulator
**Use Case**: Simulation testing, scenario replay
**Resources**: 16GB RAM, 8GB+ VRAM GPU

---

## Docker Deployment

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Nginx (Reverse Proxy)               │
│                        Port 80/443                      │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
┌────────▼────────┐             ┌────────▼────────┐
│  Trinity API    │             │  Trinity Worker │
│  (FastAPI)      │             │  (Background)   │
│  Port 8000      │             │                 │
└────────┬────────┘             └────────┬────────┘
         │                               │
         └───────────────┬───────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
┌────────▼────────┐             ┌────────▼────────┐
│   PostgreSQL    │             │     Redis       │
│   Port 5432     │             │   Port 6379     │
└─────────────────┘             └─────────────────┘

Optional Monitoring Stack:
┌─────────────────┐             ┌─────────────────┐
│   Prometheus    │────────────▶│    Grafana      │
│   Port 9090     │             │   Port 3000     │
└─────────────────┘             └─────────────────┘
```

### Environment Configuration

1. **Copy environment template**:
```bash
cp .env.example .env
```

2. **Edit configuration**:
```bash
nano .env
```

3. **Key settings**:
```bash
# Strong passwords
DB_PASSWORD=<secure_random_password>
GRAFANA_PASSWORD=<admin_password>

# GPU settings
TRINITY_USE_GPU=true
TRINITY_GPU_ID=0

# API settings
TRINITY_API_HOST=0.0.0.0
TRINITY_API_PORT=8000
```

### Service Management

**Start Services**:
```bash
docker-compose up -d
```

**Stop Services**:
```bash
docker-compose down
```

**View Logs**:
```bash
docker-compose logs -f trinity-api
```

**Restart Service**:
```bash
docker-compose restart trinity-api
```

**Scale Workers**:
```bash
docker-compose up -d --scale trinity-worker=3
```

### Data Persistence

Volumes are automatically created for data persistence:

- `postgres_data`: Database files
- `redis_data`: Redis persistence
- `prometheus_data`: Metrics data
- `grafana_data`: Dashboards and settings

Mount points:
- `./data`: Session data and recordings
- `./logs`: Application logs
- `./reports`: Generated reports
- `./models`: YOLO model weights

**Backup**:
```bash
# Backup database
docker-compose exec database pg_dump -U trinity_user trinity_av_testing > backup.sql

# Backup volumes
docker run --rm -v trinity_postgres_data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres-backup.tar.gz /data
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- NVIDIA GPU Operator installed
- StorageClass for persistent volumes

### Quick Deploy

```bash
# Create namespace
kubectl create namespace trinity

# Apply configurations
kubectl apply -f k8s/

# Check status
kubectl get pods -n trinity
```

### Kubernetes Resources

**Deployments**:
- `trinity-api`: API server (3 replicas)
- `trinity-worker`: Background workers (2 replicas)

**Services**:
- `trinity-api`: LoadBalancer (port 8000)
- `postgres`: ClusterIP (port 5432)
- `redis`: ClusterIP (port 6379)

**StatefulSets**:
- `postgres`: Database with persistent volume
- `prometheus`: Metrics storage

**Ingress**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: trinity-ingress
  namespace: trinity
spec:
  rules:
  - host: trinity.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: trinity-api
            port:
              number: 8000
```

### Scaling

**Horizontal Pod Autoscaler**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: trinity-api-hpa
  namespace: trinity
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: trinity-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Cloud Deployment

### AWS Deployment

**Using ECS (Elastic Container Service)**:

1. **Build and push image to ECR**:
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t trinity-phase2 -f docker/Dockerfile .
docker tag trinity-phase2:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/trinity-phase2:latest

# Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/trinity-phase2:latest
```

2. **Create ECS Task Definition**:
```json
{
  "family": "trinity-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "8192",
  "containerDefinitions": [
    {
      "name": "trinity-api",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/trinity-phase2:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "DB_HOST", "value": "rds-endpoint"},
        {"name": "DB_PASSWORD", "value": "from-secrets-manager"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/trinity-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

3. **Configure RDS PostgreSQL**:
```bash
# Create database instance
aws rds create-db-instance \
    --db-instance-identifier trinity-db \
    --db-instance-class db.r5.large \
    --engine postgres \
    --master-username trinity \
    --master-user-password <password> \
    --allocated-storage 100 \
    --vpc-security-group-ids sg-xxxxx
```

### Google Cloud Platform (GCP)

**Using Cloud Run**:

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/<project-id>/trinity-phase2

# Deploy to Cloud Run
gcloud run deploy trinity-api \
    --image gcr.io/<project-id>/trinity-phase2 \
    --platform managed \
    --region us-central1 \
    --memory 8Gi \
    --cpu 4 \
    --set-env-vars DB_HOST=<cloud-sql-ip>
```

### Azure Deployment

**Using Container Instances**:

```bash
# Create resource group
az group create --name trinity-rg --location eastus

# Create container instance
az container create \
    --resource-group trinity-rg \
    --name trinity-api \
    --image <your-registry>/trinity-phase2:latest \
    --cpu 4 \
    --memory 8 \
    --ports 8000 \
    --environment-variables \
        DB_HOST=<azure-database-host> \
        DB_PASSWORD=<password>
```

---

## Production Best Practices

### Security

1. **Use strong passwords**:
```bash
# Generate secure passwords
openssl rand -base64 32
```

2. **Enable SSL/TLS**:
```yaml
# nginx.conf
ssl_certificate /etc/nginx/ssl/cert.pem;
ssl_certificate_key /etc/nginx/ssl/key.pem;
ssl_protocols TLSv1.2 TLSv1.3;
```

3. **Limit exposed ports**:
```yaml
# docker-compose.yml
ports:
  - "127.0.0.1:8000:8000"  # Only local access
```

4. **Use secrets management**:
```bash
# Docker Swarm secrets
echo "my_secret_password" | docker secret create db_password -

# Kubernetes secrets
kubectl create secret generic db-password --from-literal=password=<password>
```

### Performance

1. **Enable connection pooling**:
```python
# config.yaml
database:
  pool_size: 20
  max_overflow: 40
```

2. **Use Redis caching**:
```python
# Enable Redis for caching
cache:
  enabled: true
  backend: redis
  ttl: 3600
```

3. **Optimize Docker images**:
```dockerfile
# Multi-stage build
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04  # Use runtime, not devel
```

### Reliability

1. **Health checks**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

2. **Restart policies**:
```yaml
restart: unless-stopped
```

3. **Resource limits**:
```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
    reservations:
      cpus: '2'
      memory: 4G
```

---

## Monitoring & Maintenance

### Metrics Collection

**Prometheus Metrics**:
```
# API metrics
trinity_api_requests_total
trinity_api_request_duration_seconds
trinity_api_errors_total

# Processing metrics
trinity_detection_fps
trinity_pipeline_latency_seconds
trinity_gpu_utilization_percent
```

**Grafana Dashboards**:
- System Overview
- API Performance
- Processing Pipeline
- Resource Utilization

Access Grafana: http://localhost:3000

### Log Aggregation

**View logs**:
```bash
# API logs
docker-compose logs -f trinity-api

# All services
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100 trinity-api
```

**Centralized logging** (ELK Stack):
```yaml
logging:
  driver: "fluentd"
  options:
    fluentd-address: localhost:24224
    tag: trinity.{{.Name}}
```

### Backup & Recovery

**Automated backups**:
```bash
# Cron job for daily backups
0 2 * * * /path/to/backup-script.sh
```

**Backup script**:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T database pg_dump -U trinity_user trinity_av_testing | gzip > /backups/trinity_$DATE.sql.gz
find /backups -name "trinity_*.sql.gz" -mtime +30 -delete
```

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed troubleshooting guide.

**Common Issues**:

1. **GPU not detected**:
```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

2. **Port already in use**:
```bash
sudo lsof -i :8000
kill <PID>
```

3. **Permission denied**:
```bash
sudo chown -R $USER:$USER data/ logs/
```

---

## Support

- **Documentation**: See `/docs` directory
- **Issues**: https://github.com/Sherin-SEF-AI/Trinity-Phase2/issues
- **Email**: sherin@sef-ai.com

---

**Document Version**: 1.0.0
**Last Updated**: November 2025
