# Cloud SQL Database Setup

## Overview

The Seed Planter API uses **Cloud SQL PostgreSQL** for production data storage. This provides a managed, scalable database solution with automatic backups and high availability.

## Cost-Effective Setup

We use the **db-f1-micro** tier which is:
- ✅ **Free tier eligible** (within GCP free tier limits)
- 0.6 GB RAM
- Shared CPU
- 10 GB storage (HDD)
- Perfect for development and small-scale production

## Setup Instructions

### 1. Run the Setup Script

```bash
cd /Users/roei/dev_workspace/spring-clients-projects/seedGPT
chmod +x .agents/scripts/setup_cloud_sql.sh
./.agents/scripts/setup_cloud_sql.sh
```

This script will:
1. Create a Cloud SQL PostgreSQL instance (`seedgpt-db`)
2. Create the database (`seedgpt`)
3. Create a database user with a secure password
4. Store the `DATABASE_URL` in Secret Manager
5. Output the connection details

### 2. Configuration

The database connection is automatically configured via:
- **Secret Manager**: `DATABASE_URL` secret contains the full connection string
- **Cloud Run**: Mounts the secret as an environment variable
- **Cloud SQL Proxy**: Built into Cloud Run for secure connections

### 3. Local Development

For local development, the API uses SQLite by default:
```
DATABASE_URL=sqlite:///./seedgpt.db
```

To test with PostgreSQL locally:
```bash
# Install Cloud SQL Proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.amd64
chmod +x cloud-sql-proxy

# Start proxy (replace CONNECTION_NAME with your actual connection name)
./cloud-sql-proxy --port 5432 magic-mirror-427812:us-central1:seedgpt-db

# Update .env file
DATABASE_URL=postgresql+psycopg2://seedgpt_user:PASSWORD@localhost:5432/seedgpt
```

## Database Migrations

### Initialize Database Schema

The database schema is automatically initialized on first run via `init_db()` in `main.py`.

### Future Migrations with Alembic

For schema changes, use Alembic:

```bash
cd apps/seed-planter-api

# Initialize Alembic (first time only)
alembic init alembic

# Create a migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head
```

## Monitoring & Management

### View Database Logs
```bash
gcloud sql operations list --instance=seedgpt-db --project=magic-mirror-427812
```

### Connect to Database
```bash
gcloud sql connect seedgpt-db --user=seedgpt_user --database=seedgpt --project=magic-mirror-427812
```

### Check Instance Status
```bash
gcloud sql instances describe seedgpt-db --project=magic-mirror-427812
```

## Backup & Recovery

Currently, automated backups are **disabled** to minimize costs. To enable:

```bash
gcloud sql instances patch seedgpt-db \
  --backup-start-time=03:00 \
  --enable-bin-log \
  --project=magic-mirror-427812
```

## Scaling Up

If you need more resources later:

```bash
# Upgrade to db-g1-small (1.7 GB RAM, 1 shared vCPU)
gcloud sql instances patch seedgpt-db \
  --tier=db-g1-small \
  --project=magic-mirror-427812

# Or db-n1-standard-1 (3.75 GB RAM, 1 vCPU)
gcloud sql instances patch seedgpt-db \
  --tier=db-n1-standard-1 \
  --project=magic-mirror-427812
```

## Troubleshooting

### Connection Issues

1. **Check Cloud Run has Cloud SQL connection**:
   ```bash
   gcloud run services describe seed-planter-api \
     --region=us-central1 \
     --project=magic-mirror-427812 \
     --format='value(spec.template.spec.containers[0].env)'
   ```

2. **Verify Secret Manager access**:
   ```bash
   gcloud secrets versions access latest --secret=DATABASE_URL --project=magic-mirror-427812
   ```

3. **Check Cloud SQL instance is running**:
   ```bash
   gcloud sql instances describe seedgpt-db --project=magic-mirror-427812 --format='value(state)'
   ```

### Performance Issues

- Monitor query performance in Cloud SQL logs
- Consider adding indexes to frequently queried columns
- Upgrade instance tier if needed

## Security

- ✅ Database password stored in Secret Manager
- ✅ No public IP (Cloud Run connects via Unix socket)
- ✅ Automatic SSL/TLS encryption
- ✅ IAM-based access control

## Cost Estimation

**db-f1-micro tier**:
- Instance: ~$7-10/month (or free within GCP free tier)
- Storage (10 GB HDD): ~$1.70/month
- Network egress: Minimal (internal GCP traffic)

**Total**: ~$8-12/month (or free if within GCP free tier limits)
