# SkateIQ Digital Ocean Deployment Guide

## Prerequisites

1. **Digital Ocean Account**: Sign up at https://www.digitalocean.com
2. **Docker Hub Account** (optional): For storing Docker images
3. **Domain Name** (optional): For custom domain setup

## Option 1: Deploy with Docker Compose (Recommended)

### Step 1: Create a Droplet

1. Log into Digital Ocean console
2. Create Droplet:
   - **Image**: Docker on Ubuntu 22.04
   - **Size**: Basic plan, 2GB RAM / 1 CPU ($12/month minimum recommended)
   - **Region**: Choose closest to your users
   - **Authentication**: SSH keys (recommended) or password
   - **Hostname**: `skateiq-prod`

3. Note your droplet's IP address

### Step 2: Connect to Your Droplet

```bash
ssh root@YOUR_DROPLET_IP
```

### Step 3: Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Docker Compose (if not already installed)
apt install docker-compose -y

# Install Git
apt install git -y
```

### Step 4: Clone Your Repository

```bash
# Clone your repository
git clone https://github.com/A71as/SkateIQ.git
cd SkateIQ
```

### Step 5: Configure Environment Variables

```bash
# Create .env file
cat > .env << 'EOF'
# Database
POSTGRES_DB=skateiq
POSTGRES_USER=skateiq_user
POSTGRES_PASSWORD=CHANGE_THIS_SECURE_PASSWORD

# OpenAI API
OPENAI_API_KEY=your-openai-api-key-here

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-jwt-secret-key-here

# Application
ENVIRONMENT=production
EOF

# Secure the .env file
chmod 600 .env
```

### Step 6: Build and Start Services

```bash
# Build the Docker image
docker-compose build

# Start all services in detached mode
docker-compose up -d

# Check logs
docker-compose logs -f app
```

### Step 7: Run Database Migrations

```bash
# Run the live scores migration
docker-compose exec app python migrate_live_scores.py

# Initialize database tables
docker-compose exec app python database.py
```

### Step 8: Configure Firewall

```bash
# Allow SSH
ufw allow 22/tcp

# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Allow application port
ufw allow 8001/tcp

# Enable firewall
ufw enable
```

### Step 9: Verify Deployment

```bash
# Check if services are running
docker-compose ps

# Test the API
curl http://YOUR_DROPLET_IP:8001/health

# View logs
docker-compose logs -f
```

## Option 2: Deploy Single Container (Simpler)

### Using Pre-built PostgreSQL

1. **Set up PostgreSQL**:
```bash
# Install PostgreSQL
apt install postgresql postgresql-contrib -y

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE skateiq;
CREATE USER skateiq_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE skateiq TO skateiq_user;
\q
EOF
```

2. **Build and Run Application**:
```bash
# Clone repo
git clone https://github.com/A71as/SkateIQ.git
cd SkateIQ

# Build Docker image
docker build -t skateiq-app .

# Run container
docker run -d \
  --name skateiq \
  --restart unless-stopped \
  -p 8001:8001 \
  -e DATABASE_URL="postgresql://skateiq_user:your_secure_password@host.docker.internal:5432/skateiq" \
  -e OPENAI_API_KEY="your-openai-key" \
  -e JWT_SECRET_KEY="your-jwt-secret" \
  skateiq-app

# Run migrations
docker exec skateiq python migrate_live_scores.py
docker exec skateiq python database.py
```

## Option 3: Deploy to Digital Ocean App Platform (Easiest)

### Using App Platform (No server management)

1. **Go to Digital Ocean App Platform**:
   - Click "Create App"
   - Choose "GitHub" as source
   - Select your SkateIQ repository

2. **Configure the App**:
   ```yaml
   name: skateiq
   services:
   - name: web
     github:
       repo: A71as/SkateIQ
       branch: main
     build_command: pip install -r requirements.txt
     run_command: python nhl_daily_predictions.py
     environment_slug: python
     instance_count: 1
     instance_size_slug: basic-xxs
     http_port: 8001
     envs:
     - key: OPENAI_API_KEY
       value: YOUR_KEY_HERE
       scope: RUN_TIME
     - key: JWT_SECRET_KEY
       value: YOUR_SECRET_HERE
       scope: RUN_TIME
     - key: DATABASE_URL
       value: ${db.DATABASE_URL}
       scope: RUN_TIME
   
   databases:
   - name: db
     engine: PG
     version: "15"
   ```

3. **Deploy**: Click "Create Resources"

## Setting Up a Reverse Proxy with Nginx (Optional)

### For Custom Domain and HTTPS

```bash
# Install Nginx
apt install nginx certbot python3-certbot-nginx -y

# Create Nginx config
cat > /etc/nginx/sites-available/skateiq << 'EOF'
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support for live scores
    location /ws/ {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/skateiq /etc/nginx/sites-enabled/

# Test configuration
nginx -t

# Restart Nginx
systemctl restart nginx

# Get SSL certificate (replace with your domain)
certbot --nginx -d your-domain.com -d www.your-domain.com
```

## Monitoring and Maintenance

### View Logs
```bash
# Application logs
docker-compose logs -f app

# Database logs
docker-compose logs -f postgres

# All logs
docker-compose logs -f
```

### Restart Services
```bash
# Restart everything
docker-compose restart

# Restart just the app
docker-compose restart app
```

### Update Application
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Backup Database
```bash
# Create backup
docker-compose exec postgres pg_dump -U skateiq_user skateiq > backup_$(date +%Y%m%d).sql

# Restore backup
docker-compose exec -T postgres psql -U skateiq_user skateiq < backup_20231205.sql
```

## Environment Variables Summary

Required:
- `OPENAI_API_KEY` - Your OpenAI API key
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Secret for JWT tokens (generate with `openssl rand -hex 32`)

Optional:
- `POSTGRES_DB` - Database name (default: skateiq)
- `POSTGRES_USER` - Database user (default: skateiq_user)
- `POSTGRES_PASSWORD` - Database password
- `PORT` - Application port (default: 8001)
- `ENVIRONMENT` - Environment name (production/development)

## Estimated Costs (Digital Ocean)

- **Droplet (2GB RAM)**: $12/month
- **Managed PostgreSQL**: $15/month (alternative to self-hosted)
- **App Platform (Basic)**: $5/month + database
- **Bandwidth**: First 1TB free

Total: ~$12-30/month depending on option

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs app

# Check if database is ready
docker-compose exec postgres pg_isready
```

### Database connection errors
```bash
# Verify DATABASE_URL format
echo $DATABASE_URL

# Should be: postgresql://user:password@postgres:5432/dbname
```

### Port already in use
```bash
# Find process using port 8001
netstat -tulpn | grep 8001

# Kill the process
kill -9 <PID>
```

## Next Steps

1. Set up automated backups
2. Configure monitoring (Digital Ocean Monitoring or external service)
3. Set up CI/CD pipeline with GitHub Actions
4. Configure log aggregation
5. Add application performance monitoring (APM)
