#!/bin/bash

# Update BNSF Integration Fix Script
# This script updates the server with the BNSF API fixes

set -e

echo "=== Updating BNSF Integration Fix ==="

# Check if we're in the right directory
if [ ! -f "dashboard/src/core/bnsf_integration.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Update requirements
echo "📦 Updating Python requirements..."
cd dashboard
pip install -r requirements.txt

# Run Django migrations (in case new models were added)
echo "🗄️ Running Django migrations..."
cd src
python manage.py makemigrations
python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Test the BNSF integration
echo "🧪 Testing BNSF integration..."
python ../../debug_bnsf.py

echo "✅ BNSF integration fix deployed successfully!"
echo ""
echo "Next steps:"
echo "1. Upload a BNSF certificate through the web interface"
echo "2. Test the API fetch functionality"
echo "3. Check Django logs for any remaining issues"
echo ""
echo "To check logs:"
echo "  - Django logs: tail -f /var/log/django.log"
echo "  - Nginx logs: tail -f /var/log/nginx/error.log"
echo "  - System logs: journalctl -u your-django-service -f"
