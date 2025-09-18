#!/bin/bash

# Setup Environment Script for BNSF Dashboard
# This script creates the .env file with proper values

set -e

echo "=== Setting up environment for BNSF Dashboard ==="

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists. Creating backup..."
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

# Create .env file
echo "📝 Creating .env file..."

cat > .env << 'EOF'
# Django Settings
DEBUG=True
SECRET_KEY=django-insecure-t%&8d!anzk+3%#+!3=n&^^c0auaox8wh_(x7u6hucd4d4f&zv%aj
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Settings
DB_ENGINE=django.db.backends.postgresql
DB_NAME=marium_dashboard
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=db
DB_PORT=5432

# Static and Media Files
STATIC_URL=static/
STATIC_ROOT=staticfiles
MEDIA_URL=media/
MEDIA_ROOT=media

# AWS Settings (optional - only needed if using S3 for file storage)
# AWS_ACCESS_KEY_ID=your_aws_access_key
# AWS_SECRET_ACCESS_KEY=your_aws_secret_key
# AWS_STORAGE_BUCKET_NAME=your_bucket_name
# AWS_BUCKET_FOLDER=your_folder_name
EOF

echo "✅ .env file created successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Update the database password in .env file if needed"
echo "2. Run: docker-compose up --build"
echo ""
echo "🔧 To customize settings:"
echo "   - Edit .env file with your specific values"
echo "   - Uncomment AWS settings if using S3 storage"
