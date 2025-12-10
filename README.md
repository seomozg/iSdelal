# iSdelal - AI-Powered RAG System

A complete Retrieval-Augmented Generation (RAG) system with Qdrant vector database, FastAPI backend, and an embeddable chat widget. Perfect for adding AI-powered Q&A to any website.

## ✨ Features

- **🔍 Semantic Search**: Qdrant-powered vector similarity search
- **🤖 AI Chat**: OpenAI GPT integration with context-aware responses
- **🕷️ Web Crawling**: Automated website content indexing
- **💬 Chat Widget**: Ready-to-use JavaScript widget for websites
- **🐳 Docker Ready**: Complete containerized setup
- **📊 Admin Interface**: Web-based content management
- **🔐 Secure**: API key authentication and CORS protection

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key

### 1. Clone & Setup
```bash
git clone <your-repo-url>
cd iSdelal

# Copy environment template
cp backend/.env.example backend/.env

# Edit .env with your keys
# OPENAI_API_KEY=sk-your-key-here
# API_KEY=your-random-secret-key
```

### 2. Launch Services (single compose)
```bash
docker compose up -d --build

# Check status
docker compose ps

# Health check
curl http://localhost:8000/health
```

### 3. Use the UI

- **Frontend / Admin**: http://localhost:8000/frontend/
  - Вводишь один URL сайта
  - Нажимаешь "Start Ingestion"
  - Следишь за статусом краулинга и логами
  - Видишь реальные коллекции из Qdrant
  - Генерируешь код чат‑виджета под выбранную коллекцию
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

## 📖 Documentation

| File | Description |
|------|-------------|
| [`frontend/README.md`](./frontend/README.md) | Admin interface docs (UI details) |
| [`backend/.env.example`](./backend/.env.example) | Environment configuration |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Client (Browser)                                           │
│ Embedded Widget: widget.js                                 │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/HTTPS (POST /chat)
                     │
┌────────────────────▼────────────────────────────────────────┐
│ FastAPI Backend - Port 8000                               │
│ - AI chat endpoints                                        │
│ - Content ingestion                                        │
│ - Admin interface serving                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────┐        ┌────────▼──────┐
│ Qdrant       │        │ OpenAI API    │
│ Vector DB    │        │ GPT-4.1       │
│ Port 6333    │        │ Embeddings    │
│              │        │               │
│ Collections  │        │ text-emb-3-lge│
│ Vectors      │        │               │
└──────────────┘        └───────────────┘
```

**Optional Nginx Layer:**
- Reverse proxy for production
- SSL termination
- Load balancing
- Static file serving

---

## 📁 Project Structure

```
iSdelal/
├── README.md                 # Main documentation
├── .gitignore                # Git ignore rules
├── docker-compose.yml        # Docker services config (backend + Qdrant)
│
├── backend/
│   ├── .env.example          # Environment template
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile            # Backend container
│   ├── app/
│   │   ├── main.py           # FastAPI application (API + /frontend/ + /widget)
│   │   ├── ingest.py         # Web crawler & indexing
│   │   ├── rag.py            # Vector search & LLM prompts
│   │   ├── qdrant_client.py  # Qdrant database client
│   │   └── utils.py          # Text processing utilities
│   └── tests/
│       └── test_api.py       # API tests
│
├── frontend/
│   ├── index.html            # Admin / ingestion / widget UI
│   ├── script.js             # Frontend logic, status polling, widget code
│   ├── styles.css            # Interface styling
│   └── README.md             # Frontend docs
│
└── widget/
    ├── widget.js             # Embeddable chat widget
    └── widget.css            # Widget styling
```

---

## 🔌 API Endpoints

All endpoints require `X-API-Key` header authentication.

### Health Check
```bash
GET /health
# Response: {"status": "ok"}
```

### Collections Management
```bash
GET /collections
# List all available collections

GET /collections/{name}
# Get collection statistics
```

### Content Ingestion
**Авто-краулинг сайта (один URL):**
```bash
POST /ingest
Content-Type: application/json
X-API-Key: your-api-key

{
  "url": "https://example.com",
  "collection": "example_com"
}
```

### Recent Ingestion Jobs
```bash
GET /ingest/jobs?limit=10
# Returns recent jobs with status and collection info
```

### AI Chat
```bash
POST /chat
Content-Type: application/json
X-API-Key: your-api-key

{
  "question": "What is this website about?",
  "collection": "example_site"
}

# Response:
{
  "answer": "Based on the website content...",
  "status": "ready"
}
```

### Check Ingestion Status
```bash
GET /ingest/status/{job_id}
# Returns: {
#   "status": "running" | "completed" | "failed",
#   "progress": {
#     "message": "Crawling from https://...",
#     "pages_fetched": 10,
#     "chunks_extracted": 120,
#     "embeddings_created": 120,
#     "points_upserted": 120
#   },
#   "result": {
#     "pages_crawled": 50,
#     "chunks_indexed": 197,
#     ...
#   }
# }
```

## 🧪 Testing

Run the test suite:

```bash
# In container
docker compose exec backend pytest tests/test_api.py -v

# Or locally
cd backend
pip install -r requirements.txt
pytest tests/test_api.py -v
```

**Test Coverage:**
- ✅ API authentication (X-API-Key)
- ✅ Health check endpoints
- ✅ Content ingestion & Qdrant indexing
- ✅ AI chat with RAG
- ✅ Error handling

## ⚙️ Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-key-here
API_KEY=your-random-secret-key

# Optional (defaults shown)
QDRANT_HOST=qdrant
QDRANT_PORT=6333
EMBED_MODEL=text-embedding-3-large
RAG_TOP_K=5
CRAWL_MAX_PAGES=50
CRAWL_TIMEOUT=30
USE_PLAYWRIGHT=true
```



## 🔐 Security

- ✅ API key authentication required for all endpoints
- ✅ Environment variables never committed (.env in .gitignore)
- ✅ CORS protection configured
- ✅ No sensitive data in repository

## 🔥 Production Deployment on Hosting/Server

### Prerequisites
- VPS/Dedicated server (2GB+ RAM, 20GB+ SSD)
- Domain name (yourdomain.com)
- SSL certificate (Let's Encrypt)
- Docker & Docker Compose installed
- OpenAI API key

### 1. Server Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Nginx
sudo apt install nginx -y

# Install Certbot (SSL)
sudo apt install certbot python3-certbot-nginx -y
```

### 2. Project Deployment
```bash
# Create app directory
sudo mkdir -p /var/www/isdelal
chmod 755 /var/www/isdelal

# Clone project
git clone <your-repo-url> /var/www/isdelal
cd /var/www/isdelal

# Setup environment
cp backend/.env.example backend/.env
nano backend/.env  # Edit with your API keys
```

### 3. Nginx + SSL Configuration
```bash
# Create nginx config
sudo nano /etc/nginx/sites-available/isdelal

# Paste this config (replace yourdomain.com):
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (generated by certbot)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Static files from Nginx (optional, better performance)
    location /frontend/static/ {
        alias /var/www/isdelal/frontend/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /widget/ {
        alias /var/www/isdelal/widget/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Forward everything else to backend
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # CORS for widget embedding
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, X-API-Key' always;

        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/isdelal /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. SSL Certificate Setup
```bash
# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test renewal
sudo certbot renew --dry-run

# Auto-renewal (runs monthly)
sudo systemctl enable certbot.timer
```

### 5. Environment Configuration
```bash
# Edit production .env
nano backend/.env

# Production settings:
OPENAI_API_KEY=sk-your-production-key
API_KEY=your-production-random-secret
QDRANT_HOST=qdrant
QDRANT_PORT=6333
ALLOWED_ORIGINS=https://yourdomain.com

# Performance settings
CRAWL_MAX_PAGES=100
RAG_TOP_K=10
```

### 6. Docker Production Setup
```bash
# Create production docker-compose.override.yml
nano docker-compose.prod.yml

# Production config:
version: '3.8'

services:
  backend:
    environment:
      # Additional production env vars
      - ENVIRONMENT=production
      - ALLOW_ALL_ORIGINS=false  # Use ALLOWED_ORIGINS instead

  qdrant:
    volumes:
      - /var/lib/qdrant:/qdrant/storage:rw  # Persistent data on host
```

### 7. Launch Production Services
```bash
# Start services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Check status
docker compose ps
curl https://yourdomain.com/health

# Monitor logs
docker compose logs -f backend
```

### 8. DNS Configuration
```bash
# Point your domain to server IP:
# A Record: yourdomain.com -> SERVER_IP
# CNAME: www.yourdomain.com -> yourdomain.com
```

### 9. Backup & Monitoring
```bash
# Qdrant backup script
nano /usr/local/bin/backup-qdrant.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker compose exec qdrant qdrant-backup create --name "backup_$DATE"
echo "Backup created: backup_$DATE"

# Schedule backups (crontab)
0 2 * * * /usr/local/bin/backup-qdrant.sh

# Monitor disk usage
df -h /var/lib
docker system df

# View live logs
docker compose logs --tail=100 -f backend
```

### 10. Access Your Production System

- **🔗 Landing Page**: `https://yourdomain.com/landing/`
- **🔧 Admin Dashboard**: `https://yourdomain.com/frontend/`
- **📊 API Documentation**: `https://yourdomain.com/docs`
- **💬 Widget Endpoint**: `https://yourdomain.com/widget/widget.js`

### Widget Production Code:
```html
<script>
window.AIWidgetConfig = {
  apiBase: 'https://yourdomain.com',
  collection: 'your_collection_name',
  apiKey: 'your-production-api-key',
  title: 'AI Assistant',
  welcomeMessage: 'How can I help you?'
};
</script>
<script src="https://yourdomain.com/widget/widget.js"></script>
```

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| `docker compose up` fails | Ensure Docker Desktop is running |
| API not responding | Check `docker compose logs backend` |
| Hot reload not working | Restart with `docker compose restart backend` |
| Qdrant data lost | Use `docker compose down` (not `down -v`) to preserve data |
| OpenAI API errors | Verify `OPENAI_API_KEY` in `.env` |
| SSL cert expired | Run `sudo certbot renew` |
| Domain not working | Check DNS propagation (may take 24-48h) |
| Service crashes | Check system resources: `htop` , free memory `free -h` |

**Full Diagnostics:**
```bash
docker compose ps              # Container status
docker compose logs backend    # Backend logs
docker compose logs qdrant     # Qdrant logs
curl http://localhost:8000/health  # API health check
```

## 📄 License

MIT License - see repository for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📞 Support

- 📖 **Documentation**: Check the `/docs` folder
- 🐛 **Issues**: Open a GitHub issue
- 💬 **Discussions**: Use GitHub Discussions for questions
