#!/bin/bash

# SkateIQ Quick Deploy Script for Digital Ocean
# This script automates the deployment process

set -e  # Exit on error

echo "🏒 SkateIQ Digital Ocean Deployment Script"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install required packages
echo "📦 Installing required packages..."
apt install -y docker.io docker-compose git ufw

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Configure firewall
echo "🔒 Configuring firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8001/tcp
echo "y" | ufw enable

# Clone repository (if not already cloned)
if [ ! -d "/opt/skateiq" ]; then
    echo "📥 Cloning SkateIQ repository..."
    cd /opt
    git clone https://github.com/A71as/SkateIQ.git skateiq
    cd skateiq
else
    echo "📥 Repository already exists, pulling latest changes..."
    cd /opt/skateiq
    git pull origin main
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    read -p "Enter your OpenAI API Key: " openai_key
    read -p "Enter PostgreSQL password: " db_password
    
    # Generate JWT secret
    jwt_secret=$(openssl rand -hex 32)
    
    cat > .env << EOF
# Database
POSTGRES_DB=skateiq
POSTGRES_USER=skateiq_user
POSTGRES_PASSWORD=$db_password

# OpenAI API
OPENAI_API_KEY=$openai_key

# JWT Secret
JWT_SECRET_KEY=$jwt_secret

# Application
ENVIRONMENT=production
EOF
    
    chmod 600 .env
    echo "✅ .env file created"
else
    echo "⚠️  .env file already exists, skipping..."
fi

# Build and start services
echo "🐳 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Run database migrations
echo "💾 Running database migrations..."
docker-compose exec -T app python database.py
docker-compose exec -T app python migrate_live_scores.py

# Check service status
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🌐 Your application should be running at:"
echo "   http://$(curl -s ifconfig.me):8001"
echo ""
echo "📝 Useful commands:"
echo "   View logs:        cd /opt/skateiq && docker-compose logs -f"
echo "   Restart app:      cd /opt/skateiq && docker-compose restart"
echo "   Stop app:         cd /opt/skateiq && docker-compose down"
echo "   Update app:       cd /opt/skateiq && git pull && docker-compose up -d --build"
echo ""
echo "🔐 Remember to:"
echo "   1. Update your .env file with production credentials"
echo "   2. Set up SSL/TLS with Let's Encrypt"
echo "   3. Configure regular database backups"
echo ""
