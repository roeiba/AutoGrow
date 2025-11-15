#!/bin/bash
# Setup Cloud SQL PostgreSQL database (free tier eligible)

set -e

PROJECT_ID="magic-mirror-427812"
REGION="us-central1"
INSTANCE_NAME="seedgpt-db"
DATABASE_NAME="seedgpt"
DB_USER="seedgpt_user"

echo "🗄️  Setting up Cloud SQL PostgreSQL database..."
echo ""
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Instance: $INSTANCE_NAME"
echo ""

# Check if instance already exists
if gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID &>/dev/null; then
    echo "✅ Instance '$INSTANCE_NAME' already exists"
else
    echo "📦 Creating Cloud SQL instance (this takes ~5-10 minutes)..."
    
    # Create a shared-core instance (db-f1-micro is free tier eligible)
    # - db-f1-micro: 0.6 GB RAM, shared CPU (cheapest option)
    # - 10 GB storage (minimum)
    # - Automated backups disabled to save costs (can enable later)
    gcloud sql instances create $INSTANCE_NAME \
        --project=$PROJECT_ID \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-type=HDD \
        --storage-size=10GB \
        --storage-auto-increase \
        --backup-start-time=03:00 \
        --no-backup \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=3 \
        --availability-type=zonal \
        --no-assign-ip
    
    echo "✅ Instance created successfully!"
fi

# Create database if it doesn't exist
echo ""
echo "📊 Creating database '$DATABASE_NAME'..."
gcloud sql databases create $DATABASE_NAME \
    --instance=$INSTANCE_NAME \
    --project=$PROJECT_ID \
    2>/dev/null || echo "Database already exists"

# Generate a secure random password
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Create database user
echo ""
echo "👤 Creating database user '$DB_USER'..."
gcloud sql users create $DB_USER \
    --instance=$INSTANCE_NAME \
    --password="$DB_PASSWORD" \
    --project=$PROJECT_ID \
    2>/dev/null || echo "User already exists (will update password)"

# If user exists, update password
gcloud sql users set-password $DB_USER \
    --instance=$INSTANCE_NAME \
    --password="$DB_PASSWORD" \
    --project=$PROJECT_ID \
    2>/dev/null || true

# Get connection name
CONNECTION_NAME=$(gcloud sql instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format='value(connectionName)')

echo ""
echo "✅ Cloud SQL setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Database Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Connection Name: $CONNECTION_NAME"
echo "Database: $DATABASE_NAME"
echo "User: $DB_USER"
echo "Password: $DB_PASSWORD"
echo ""
echo "Database URL (for Cloud Run):"
echo "postgresql+psycopg2://$DB_USER:$DB_PASSWORD@/$DATABASE_NAME?host=/cloudsql/$CONNECTION_NAME"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Store credentials in Secret Manager
echo "🔐 Storing database credentials in Secret Manager..."

# Create or update DATABASE_URL secret
echo -n "postgresql+psycopg2://$DB_USER:$DB_PASSWORD@/$DATABASE_NAME?host=/cloudsql/$CONNECTION_NAME" | \
    gcloud secrets create DATABASE_URL \
    --project=$PROJECT_ID \
    --data-file=- \
    --replication-policy="automatic" \
    2>/dev/null || \
    echo -n "postgresql+psycopg2://$DB_USER:$DB_PASSWORD@/$DATABASE_NAME?host=/cloudsql/$CONNECTION_NAME" | \
    gcloud secrets versions add DATABASE_URL \
    --project=$PROJECT_ID \
    --data-file=-

echo "✅ Secret 'DATABASE_URL' created/updated in Secret Manager"
echo ""

# Update Cloud Run service to use the database
echo "🚀 Next steps:"
echo ""
echo "1. Update your Cloud Run deployment to:"
echo "   - Add --add-cloudsql-instances=$CONNECTION_NAME"
echo "   - Update secret: DATABASE_URL=DATABASE_URL:latest"
echo ""
echo "2. The workflow will be updated automatically"
echo ""

# Save configuration to file
cat > /tmp/cloud_sql_config.txt <<EOF
CONNECTION_NAME=$CONNECTION_NAME
DATABASE_NAME=$DATABASE_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DATABASE_URL=postgresql+psycopg2://$DB_USER:$DB_PASSWORD@/$DATABASE_NAME?host=/cloudsql/$CONNECTION_NAME
EOF

echo "💾 Configuration saved to: /tmp/cloud_sql_config.txt"
echo ""
echo "🎉 Setup complete! Database is ready to use."
