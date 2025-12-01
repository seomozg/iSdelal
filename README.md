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
cd isdelal

# Copy environment template
cp backend/.env.example backend/.env

# Edit .env with your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here
# API_KEY=your-random-secret-key
```

### 2. Launch Services
```bash
# IMPORTANT: Start services in correct order!
docker compose up -d qdrant
sleep 5
docker compose up --build -d backend
sleep 10
docker compose up --build -d nginx

# Check status
docker compose ps
```

### 3. Access Interfaces
- **Admin Interface**: http://localhost:8000/frontend/
- **API Documentation**: http://localhost:8000/docs
- **Direct API**: http://localhost:8000/health
- **Production**: https://your-domain.com/health

## 📖 Documentation

| File | Description |
|------|-------------|
| [`DEPLOY.md`](./DEPLOY.md) | Production deployment guide |
| [`WIDGET_README.md`](./WIDGET_README.md) | Widget integration guide |
| [`frontend/README.md`](./frontend/README.md) | Admin interface docs |
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
├── DEPLOY.md                 # Production deployment
├── WIDGET_README.md          # Widget integration guide
├── .gitignore                # Git ignore rules
├── docker-compose.yml        # Docker services config
│
├── backend/
│   ├── .env.example          # Environment template
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile           # Backend container
│   ├── app/
│   │   ├── main.py          # FastAPI application
│   │   ├── ingest.py        # Web crawler & indexing
│   │   ├── rag.py           # Vector search & LLM prompts
│   │   ├── qdrant_client.py # Qdrant database client
│   │   └── utils.py         # Text processing utilities
│   └── tests/
│       └── test_api.py      # API tests
│
├── frontend/
│   ├── index.html           # Admin interface
│   ├── script.js            # Frontend logic
│   ├── styles.css           # Interface styling
│   └── README.md            # Frontend docs
│
├── widget/
│   ├── widget.js            # Chat widget for websites
│   ├── widget.css           # Widget styling
│   └── widget_example.html  # Widget demo page
│
└── nginx/
    ├── default.conf         # Nginx configuration
    └── Dockerfile           # Nginx container
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

**Auto-crawl website:**
```bash
POST /ingest
Content-Type: application/json
X-API-Key: your-api-key

{
  "url": "https://example.com",
  "collection": "example_site"
}
```

**Specific URLs:**
```bash
POST /ingest
Content-Type: application/json
X-API-Key: your-api-key

{
  "urls": [
    "https://example.com/page1",
    "https://example.com/page2"
  ],
  "collection": "example_site"
}
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
  "answer": "Based on the website content..."
}
```

### Check Ingestion Status
```bash
GET /ingest/status/{job_id}
# Returns: {"status": "completed", "result": {...}}
```

---

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

---

## 💬 Widget Integration

Add the AI chat widget to any website:

```html
<!-- Configure the widget -->
<script>
window.AIWidgetConfig = {
  apiBase: 'http://localhost:8000',        // Your API URL
  collection: 'court_craze',               // Collection name
  apiKey: 'your-api-key',                  // From .env API_KEY
  title: 'AI Assistant',                   // Widget title
  welcomeMessage: 'Hello! How can I help?' // Welcome message
};
</script>

<!-- Load the widget -->
<script src="http://localhost:8000/widget/widget.js"></script>
```

**Available Collections:**
- `court_craze` - Padel tennis (13 chunks)
- `joyreactor_multi` - Entertainment (16 chunks)
- `tbank_multi` - Banking services (14 chunks)

**Programmatic Control:**
```javascript
// Initialize
AIWidget.init({
  collection: 'court_craze',
  title: 'Sports AI'
});

// Toggle visibility
AIWidget.toggle();

// Send message
AIWidget.sendMessage('Hello AI!');
```

---

## 🔐 Security

- ✅ API key authentication required for all endpoints
- ✅ Environment variables never committed (.env in .gitignore)
- ✅ CORS protection configured
- ✅ No sensitive data in repository

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| `docker compose up` fails | Ensure Docker Desktop is running |
| API not responding | Check `docker compose logs backend` |
| Hot reload not working | Restart with `docker compose restart backend` |
| Qdrant data lost | Use `docker compose down` (not `down -v`) to preserve data |
| OpenAI API errors | Verify `OPENAI_API_KEY` in `.env` |

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


