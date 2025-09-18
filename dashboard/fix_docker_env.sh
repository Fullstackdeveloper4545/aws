#!/bin/bash

# Fix Docker Environment Variables Script
# This script fixes the invalid environment variable issue

set -e

echo "=== Fixing Docker Environment Variables ==="

# Navigate to dashboard directory
cd dashboard

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

echo "🔍 Checking for environment issues..."

# Check if .env exists and has invalid variables
if [ -f ".env" ]; then
    echo "📄 Found existing .env file"
    
    # Check for lines with = at the beginning (invalid format)
    if grep -q "^=" .env; then
        echo "⚠️  Found invalid environment variables (lines starting with =)"
        echo "🔧 Fixing .env file..."
        
        # Create backup
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        echo "📋 Backup created: .env.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Remove invalid lines and create new .env
        grep -v "^=" .env > .env.tmp
        mv .env.tmp .env
        echo "✅ Removed invalid environment variables"
    else
        echo "✅ .env file looks good"
    fi
else
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "✅ .env file created"
fi

# Ensure .env has proper format
echo "🔧 Ensuring proper .env format..."

# Remove any lines that start with = or are empty
sed -i '/^=/d' .env
sed -i '/^$/d' .env

echo "✅ Environment file fixed!"

# Test Docker Compose configuration
echo "🧪 Testing Docker Compose configuration..."
if docker-compose config > /dev/null 2>&1; then
    echo "✅ Docker Compose configuration is valid"
else
    echo "❌ Docker Compose configuration has errors:"
    docker-compose config
    exit 1
fi

echo ""
echo "🚀 Ready to deploy! Run:"
echo "   docker-compose up --build"
echo ""
echo "📋 If you still get errors:"
echo "   1. Check Docker logs: docker-compose logs"
echo "   2. Verify .env file: cat .env"
echo "   3. Test config: docker-compose config"
