// RAG Frontend JavaScript
class RAGFrontend {
    constructor() {
        this.apiBase = 'http://localhost:8000';
        this.currentJobId = null;
        this.statusCheckInterval = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadCollections();
        this.updateWidgetCode();
        this.addLogEntry('System initialized. Ready for content ingestion.');
    }

    bindEvents() {
        // Ingestion form
        document.getElementById('ingest-btn').addEventListener('click', () => this.startIngestion());

        // Widget configuration
        document.getElementById('widget-collection').addEventListener('change', () => this.updateWidgetCode());
        document.getElementById('widget-title').addEventListener('input', () => this.updateWidgetCode());
        document.getElementById('widget-message').addEventListener('input', () => this.updateWidgetCode());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                this.startIngestion();
            }
        });
    }

    async startIngestion() {
        const urlInput = document.getElementById('url-input').value.trim();
        const urlsInput = document.getElementById('urls-input').value.trim();
        const collectionInput = document.getElementById('collection-input').value.trim();

        if (!urlInput && !urlsInput) {
            this.showError('Please enter at least one URL');
            return;
        }

        if (!collectionInput) {
            this.showError('Please enter a collection name');
            return;
        }

        // Prepare request data
        const requestData = {
            collection: collectionInput
        };

        if (urlsInput) {
            // Multiple URLs
            requestData.urls = urlsInput.split('\n').map(url => url.trim()).filter(url => url);
        } else {
            // Single URL (crawling)
            requestData.url = urlInput;
        }

        try {
            this.setStatus('running', 'Starting ingestion...');
            this.addLogEntry(`🚀 Starting ingestion for collection: ${collectionInput}`);

            const response = await fetch(`${this.apiBase}/ingest`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': 'aB3fK9mN2pQ7rT8vX1zC4eG6hJ0nL5aB3fK9mN2pQ7rT8vX1zC4eG6hJ0nL5'
                },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();

            if (response.ok) {
                this.currentJobId = data.job_id;
                this.addLogEntry(`✅ Ingestion job started with ID: ${this.currentJobId}`);
                this.startStatusChecking();
            } else {
                throw new Error(data.detail || 'Ingestion failed');
            }
        } catch (error) {
            this.setStatus('failed', 'Error');
            this.addLogEntry(`❌ Error: ${error.message}`, 'error');
            console.error('Ingestion error:', error);
        }
    }

    startStatusChecking() {
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
        }

        this.statusCheckInterval = setInterval(async () => {
            try {
                const response = await fetch(`${this.apiBase}/ingest/status/${this.currentJobId}`, {
                    headers: {
                        'X-API-Key': 'aB3fK9mN2pQ7rT8vX1zC4eG6hJ0nL5aB3fK9mN2pQ7rT8vX1zC4eG6hJ0nL5'
                    }
                });

                const data = await response.json();

                this.updateStatusDisplay(data);

                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(this.statusCheckInterval);
                    this.statusCheckInterval = null;

                    if (data.status === 'completed') {
                        this.addLogEntry(`🎉 Ingestion completed! ${data.result.pages_indexed} pages, ${data.result.chunks_indexed} chunks indexed.`, 'success');
                        this.loadCollections(); // Refresh collections list
                    } else {
                        this.addLogEntry(`❌ Ingestion failed: ${data.error}`, 'error');
                    }
                }
            } catch (error) {
                console.error('Status check error:', error);
                this.addLogEntry(`⚠️ Status check failed: ${error.message}`, 'warning');
            }
        }, 2000); // Check every 2 seconds
    }

    updateStatusDisplay(data) {
        const statusText = document.getElementById('status-text');
        const jobIdText = document.getElementById('job-id');
        const progressText = document.getElementById('progress-text');

        // Update status
        statusText.textContent = this.capitalizeFirst(data.status);
        statusText.className = `status-value status-${data.status}`;

        // Update job ID
        jobIdText.textContent = this.currentJobId || '-';

        // Update progress
        if (data.result) {
            progressText.textContent = `${data.result.pages_indexed || 0} pages, ${data.result.chunks_indexed || 0} chunks`;
        } else {
            progressText.textContent = 'In progress...';
        }
    }

    async loadCollections() {
        try {
            const response = await fetch(`${this.apiBase.replace('/api', '')}/collections`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            const collectionsList = document.getElementById('collections-list');
            collectionsList.innerHTML = '';

            if (data.collections && data.collections.length > 0) {
                data.collections.forEach(collection => {
                    this.addCollectionCard(collection.name);
                });
            } else {
                collectionsList.innerHTML = '<div class="collection-loading">No collections found</div>';
            }
        } catch (error) {
            console.error('Error loading collections:', error);
            document.getElementById('collections-list').innerHTML =
                '<div class="collection-loading">Error loading collections</div>';
        }
    }

    addCollectionCard(collectionName) {
        const collectionsList = document.getElementById('collections-list');

        const card = document.createElement('div');
        card.className = 'collection-card';
        card.innerHTML = `
            <div class="collection-name">${collectionName}</div>
            <div class="collection-stats">
                <div class="collection-stat">
                    <span>📊</span>
                    <span>Loading...</span>
                </div>
            </div>
        `;

        collectionsList.appendChild(card);

        // Load collection stats
        this.loadCollectionStats(collectionName, card);
    }

    async loadCollectionStats(collectionName, cardElement) {
        try {
            const response = await fetch(`${this.apiBase.replace('/api', '')}/collections/${collectionName}`);
            const data = await response.json();

            if (data.points_count !== undefined) {
                const statsDiv = cardElement.querySelector('.collection-stats');
                statsDiv.innerHTML = `
                    <div class="collection-stat">
                        <span>📄</span>
                        <span>${data.points_count} chunks</span>
                    </div>
                    <div class="collection-stat">
                        <span>🔍</span>
                        <span>${data.indexed_vectors_count || 0} indexed</span>
                    </div>
                `;
            }
        } catch (error) {
            console.error(`Error loading stats for ${collectionName}:`, error);
            // Show error in the UI
            const statsDiv = cardElement.querySelector('.collection-stats');
            statsDiv.innerHTML = `
                <div class="collection-stat">
                    <span>❌</span>
                    <span>Error loading</span>
                </div>
            `;
        }
    }

    updateWidgetCode() {
        const collection = document.getElementById('widget-collection').value;
        const title = document.getElementById('widget-title').value;
        const message = document.getElementById('widget-message').value;

        const code = `<script>
window.AIWidgetConfig = {
  apiBase: '${this.apiBase}',
  collection: '${collection}',
  apiKey: 'aB3fK9mN2pQ7rT8vX1zC4eG6hJ0nL5aB3fK9mN2pQ7rT8vX1zC4eG6hJ0nL5',
  title: '${title}',
  language: 'en',
  welcomeMessage: '${message}'
};
</script>
<script src="${this.apiBase}/widget/widget.js"></script>`;

        document.getElementById('widget-code').textContent = code;
    }

    setStatus(status, text) {
        const statusText = document.getElementById('status-text');
        statusText.textContent = text;
        statusText.className = `status-value status-${status}`;
    }

    addLogEntry(message, type = 'info') {
        const logsContainer = document.getElementById('logs');
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${type}`;
        logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;

        logsContainer.appendChild(logEntry);
        logsContainer.scrollTop = logsContainer.scrollHeight;

        // Keep only last 50 entries
        while (logsContainer.children.length > 50) {
            logsContainer.removeChild(logsContainer.children[0]);
        }
    }

    showError(message) {
        this.addLogEntry(`❌ ${message}`, 'error');
        alert(message);
    }

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
}

// Global copy function
function copyCode() {
    const codeElement = document.getElementById('widget-code');
    const range = document.createRange();
    range.selectNodeContents(codeElement);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);

    try {
        document.execCommand('copy');
        const copyBtn = document.querySelector('.copy-btn');
        const originalText = copyBtn.textContent;
        copyBtn.textContent = '✅ Copied!';
        copyBtn.style.background = '#48bb78';

        setTimeout(() => {
            copyBtn.textContent = originalText;
            copyBtn.style.background = '';
        }, 2000);
    } catch (err) {
        console.error('Failed to copy: ', err);
    }

    selection.removeAllRanges();
}

// Initialize the frontend when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new RAGFrontend();
});
