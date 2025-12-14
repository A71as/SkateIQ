#!/bin/bash
# Deployment webhook script for SkateIQ
# This script should be placed on your server and called via a webhook

set -e

echo "📦 Starting SkateIQ deployment..."

cd /opt/skateiq

echo "🔄 Pulling latest changes from GitHub..."
git pull origin main

echo "🛑 Stopping containers..."
docker-compose down

echo "🔨 Building new images..."
docker-compose build --no-cache

echo "🚀 Starting containers..."
docker-compose up -d

echo "⏳ Waiting for containers to start..."
sleep 15

echo "🔄 Running database migrations..."
docker-compose exec -T app python migrate_live_scores.py || echo "Migration not needed"

echo "✅ Deployment complete!"
echo "🏥 Container status:"
docker-compose ps
