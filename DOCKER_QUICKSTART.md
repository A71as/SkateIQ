# 🐳 Docker Deployment Quick Start

## Local Testing with Docker

### Test the container locally before deploying:

```bash
# Build the image
docker build -t skateiq .

# Run with environment variables
docker run -p 8001:8001 \
  -e OPENAI_API_KEY="your-key" \
  -e DATABASE_URL="sqlite:///./skateiq.db" \
  -e JWT_SECRET_KEY="test-secret" \
  skateiq

# Test the app
curl http://localhost:8001/health
```

## Deploy to Digital Ocean - 3 Simple Steps

### 1️⃣ Create a Droplet

```bash
# On Digital Ocean dashboard:
- Click "Create" → "Droplets"
- Choose: Docker on Ubuntu 22.04
- Size: 2GB RAM / 1 CPU ($12/month)
- Add your SSH key
- Create Droplet
```

### 2️⃣ Run the Deploy Script

```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Download and run the deploy script
curl -sSL https://raw.githubusercontent.com/A71as/SkateIQ/main/deploy.sh | bash
```

### 3️⃣ You're Live! 🎉

Visit: `http://YOUR_DROPLET_IP:8001`

## Manual Deployment (Alternative)

```bash
# 1. SSH into your server
ssh root@YOUR_DROPLET_IP

# 2. Clone the repository
git clone https://github.com/A71as/SkateIQ.git
cd SkateIQ

# 3. Create environment file
cat > .env << EOF
OPENAI_API_KEY=your-openai-key-here
POSTGRES_PASSWORD=secure-password-here
JWT_SECRET_KEY=$(openssl rand -hex 32)
EOF

# 4. Start everything with Docker Compose
docker-compose up -d

# 5. Run migrations
docker-compose exec app python database.py
docker-compose exec app python migrate_live_scores.py

# 6. Check it's running
curl http://localhost:8001/health
```

## Common Commands

```bash
# View logs
docker-compose logs -f app

# Restart the app
docker-compose restart app

# Stop everything
docker-compose down

# Update to latest code
git pull && docker-compose up -d --build

# Backup database
docker-compose exec postgres pg_dump -U skateiq_user skateiq > backup.sql
```

## Environment Variables

Add these to your `.env` file:

```bash
# Required
OPENAI_API_KEY=sk-...                    # Your OpenAI API key
POSTGRES_PASSWORD=secure_password123     # Database password
JWT_SECRET_KEY=random_64_char_string     # Generate with: openssl rand -hex 32

# Optional
POSTGRES_DB=skateiq                      # Database name
POSTGRES_USER=skateiq_user              # Database user
PORT=8001                                # Application port
```

## Troubleshooting

**Can't connect to the app?**
```bash
# Check if containers are running
docker-compose ps

# Check app logs
docker-compose logs app

# Check if port is open
curl http://localhost:8001/health
```

**Database errors?**
```bash
# Check database is running
docker-compose exec postgres pg_isready

# Reset database
docker-compose down -v
docker-compose up -d
docker-compose exec app python database.py
```

## Full Documentation

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide including:
- SSL/HTTPS setup
- Custom domain configuration
- Monitoring and backups
- CI/CD pipeline
- Performance tuning
