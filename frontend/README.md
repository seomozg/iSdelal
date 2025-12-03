# RAG System Frontend

A modern web interface for the RAG (Retrieval-Augmented Generation) system that allows users to:

- 🚀 **Ingest website content** through a single URL input
- 📊 **Monitor ingestion progress** with detailed status and logs
- 🎨 **Generate AI chat widgets** with customizable configuration
- 📚 **View available collections** (from Qdrant) with statistics

## Features

### Content Ingestion
- **Single URL Crawling**: Enter one URL to crawl the entire website
- **Auto-generated collection name**: Collection is derived from the domain (e.g. `https://www.moose-farm.ru/` → `moose_farm_ru`)
- **Detailed Progress**: Status shows phase and counters (pages fetched, chunks, embeddings, points)
- **Activity Logging**: Timestamped log entries for each step of ingestion

### Widget Generation
- **Custom Configuration**: Set collection, title, welcome message
- **Code Generation**: Automatically generates embeddable JavaScript code
- **Collection Selection**: Choose from available ingested collections
- **Copy to Clipboard**: One-click code copying

### Collection Management
- **Live Statistics**: View chunk counts and indexing status
- **Collection Overview**: See all available content collections
- **Real-time Updates**: Collections refresh after successful ingestion

## Usage

### Starting the Frontend

1. **Ensure backend is running:**
   ```bash
   docker compose up -d
   ```

2. **Access the frontend:**
   ```
   http://localhost:8000/frontend/
   ```

### Ingesting Content

1. **Enter a website URL** in the URL field (e.g. `https://www.moose-farm.ru/`)
2. Коллекция будет **сгенерирована автоматически** из домена и сохранена в скрытом поле
3. **Click "Start Ingestion"**
4. **Monitor progress** in the status section:
   - статус джобы (`pending/running/completed/failed`)
   - Job ID
   - строка `Progress` с фазой и счётчиками
5. **View logs** for detailed activity (все действия с метками времени)

### Generating Widgets

1. **Select a collection** from the dropdown (список берётся из `/collections` в Qdrant)
2. **Customize title and welcome message**
3. **Copy the generated code** из блока `Integration Code`
4. **Paste into your website's HTML** — это подключит чат‑виджет, который будет использовать выбранную коллекцию
5. Демо‑виджет на этой же странице автоматически обновляется под выбранную коллекцию и настройки

## API Integration

The frontend communicates with these backend endpoints:

- `POST /ingest` - Start content ingestion
- `GET /ingest/status/{job_id}` - Monitor ingestion progress
- `GET /collections` - List available collections
- `GET /collections/{name}` - Get collection statistics
- `POST /chat` - Test chat functionality

## File Structure

```
frontend/
├── index.html          # Main interface
├── styles.css          # Modern responsive styling
├── script.js           # Frontend logic and API calls
└── README.md          # This documentation
```

## Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Development

### Adding New Features

1. **Update HTML** in `index.html` for new UI elements
2. **Add styles** in `styles.css` for visual design
3. **Implement logic** in `script.js` for functionality
4. **Test thoroughly** with different collections and URLs

### Customization

The interface is fully customizable:

- **Colors**: Modify CSS custom properties in `:root`
- **Layout**: Adjust grid templates and responsive breakpoints
- **Functionality**: Extend the `RAGFrontend` class methods

## Troubleshooting

### Frontend Not Loading
- Ensure backend is running: `docker compose ps`
- Check logs: `docker compose logs backend`
- Verify files are mounted: Check docker-compose.yml volumes

### Ingestion Failing
- Check URL format (must include http/https)
- Verify collection name doesn't contain special characters
- Monitor logs for specific error messages

### Widget Code Not Working
- Ensure collection exists and has content (проверь раздел *Available Collections*)
- Check API key configuration (значение `API_KEY` в `backend/.env`)
- Verify backend CORS settings

## Security Notes

- The frontend includes the API key in client-side code for demonstration
- In production, implement proper authentication
- Consider server-side widget code generation
- Use HTTPS for all production deployments

## Contributing

1. Test all features with different website types
2. Ensure responsive design works on mobile devices
3. Add proper error handling for edge cases
4. Update documentation for new features

