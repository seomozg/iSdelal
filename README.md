# iSdelal - AI-Powered RAG System

A complete Retrieval-Augmented Generation (RAG) system with Qdrant vector database, FastAPI backend, and an embeddable chat widget. Perfect for adding AI-powered Q&A to any website.

## ✨ Features

- **🔍 Semantic Search**: Qdrant-powered vector similarity search
- **🤖 AI Chat**: OpenAI GPT integration with context-aware responses
- **🕷️ Web Crawling**: Automated website content indexing
- **💬 Chat Widget**: Ready-to-use JavaScript widget for websites
- **🐳 Docker Ready**: Complete containerized setup
- **📊 Admin Interface**: Web-based content management
- **🔐 Secure**: CORS protection configured

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

All endpoints are open access without authentication.

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

{
  "url": "https://example.com",
  "collection": "example_com"
}
```

### AI Chat
```bash
POST /chat
Content-Type: application/json

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
- ✅ Health check endpoints
- ✅ Content ingestion & Qdrant indexing
- ✅ AI chat with RAG
- ✅ Error handling

## ⚙️ Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-key-here

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

После того как ты проингестил сайт и появилась коллекция (например, `moose_farm_ru`), виджет подключается так:

```html
<!-- Configure the widget -->
<script>
window.AIWidgetConfig = {
  apiBase: 'http://localhost:8000',        // Backend URL
  collection: 'moose_farm_ru',             // Имя коллекции из Qdrant
  title: 'AI Assistant',                   // Заголовок виджета
  welcomeMessage: 'Hello! How can I help?' // Приветственное сообщение
};
</script>

<!-- Load the widget -->
<script src="http://localhost:8000/widget/widget.js"></script>
```

Код выше автоматически генерируется на странице `http://localhost:8000/frontend/` в блоке **AI Chat Widget**. Ты выбираешь коллекцию, настраиваешь заголовок и приветствие — и просто копируешь готовый `<script>`‑блок.

---

## 🔐 Security

- ✅ Open access API (no authentication required)
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
