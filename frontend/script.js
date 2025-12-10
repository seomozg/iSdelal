// RAG Frontend JavaScript
class RAGFrontend {
    // Function to generate collection name from URL
    generateCollectionName(rawUrl) {
        try {
            let normalized = rawUrl.trim();

            // If user entered domain without scheme (moose-farm.ru or www.moose-farm.ru),
            // prepend https:// so that URL() doesn't throw.
            if (!/^https?:\/\//i.test(normalized)) {
                normalized = 'https://' + normalized;
            }

            const parsed = new URL(normalized);
            const domain = parsed.hostname.replace(/^www\./, ''); // Remove www. prefix

            // Generate collection name from domain
            const collectionName = domain.replace(/[^a-zA-Z0-9]/g, '_'); // Replace non-alphanumeric with underscore

            return collectionName.toLowerCase();
        } catch (error) {
            console.error('Error generating collection name:', error, 'for input:', rawUrl);
            return 'default_collection';
        }
    }
    constructor() {
        this.apiBase = 'http://localhost:8000';
        this.currentJobId = null;
        this.statusCheckInterval = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadCollections();
        this.loadActiveProcesses(); // Load active ingestion processes
        this.updateWidgetCode();
        this.restoreJobFromStorage();
        this.addLogEntry('System initialized. Ready for content ingestion.');

        // Auto-refresh active processes every 30 seconds
        setInterval(() => this.loadActiveProcesses(), 30000);
    }

    restoreJobFromStorage() {
        try {
            const storedJobId = localStorage.getItem('rag_current_job_id');
            if (!storedJobId) return;

            this.currentJobId = storedJobId;

            // single status check to see if job is still active
            fetch(`${this.apiBase}/ingest/status/${this.currentJobId}`)
                .then(res => res.json())
                .then(data => {
                    this.updateStatusDisplay(data);

                    if (data.status === 'running') {
                        this.addLogEntry(`Resumed monitoring job ${this.currentJobId}.`);
                        this.startStatusChecking();
                    } else {
                        // job already finished, clear stored id
                        localStorage.removeItem('rag_current_job_id');
                    }
                })
                .catch(err => {
                    console.error('Failed to restore job from storage:', err);
                });
        } catch (e) {
            console.error('Error accessing localStorage:', e);
        }
    }

    bindEvents() {
        // Ingestion form
        document.getElementById('ingest-btn').addEventListener('click', () => this.startIngestion());
        
        // Auto-update collection name when URL changes
        document.getElementById('url-input').addEventListener('input', (e) => {
            const url = e.target.value.trim();
            if (url) {
                const collectionName = this.generateCollectionName(url);
                document.getElementById('collection-input').value = collectionName;
            }
        });

        // Widget configuration
        document.getElementById('widget-collection').addEventListener('change', () => this.updateWidgetCode());
        document.getElementById('widget-title').addEventListener('input', () => this.updateWidgetCode());
        document.getElementById('widget-message').addEventListener('input', () => this.updateWidgetCode());
        document.getElementById('widget-color').addEventListener('input', () => this.updateWidgetCode());
        document.getElementById('widget-send-text').addEventListener('input', () => this.updateWidgetCode());
        document.getElementById('widget-placeholder').addEventListener('input', () => this.updateWidgetCode());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                this.startIngestion();
            }
        });

        // Active processes refresh button
        const refreshBtn = document.getElementById('refresh-processes-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadActiveProcesses());
        }
    }

    async startIngestion() {
        const urlInput = document.getElementById('url-input').value.trim();
        
        if (!urlInput) {
            this.showError('Please enter a URL');
            return;
        }

        // Generate collection name from URL
        const collectionInput = this.generateCollectionName(urlInput);
        document.getElementById('collection-input').value = collectionInput;
        console.log(`🎯 Generated collection name: "${collectionInput}" for URL: "${urlInput}"`);

        if (!collectionInput) {
            this.showError('Please enter a collection name');
            return;
        }

        // Prepare request data
        const requestData = {
            collection: collectionInput,
            url: urlInput
        };

        try {
            this.setStatus('running', 'Starting ingestion...');
            this.addLogEntry(`🚀 Starting ingestion for collection: ${collectionInput}`);

            const response = await fetch(`${this.apiBase}/ingest`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();

            if (response.ok) {
                this.currentJobId = data.job_id;
                try {
                    localStorage.setItem('rag_current_job_id', this.currentJobId);
                } catch (e) {
                    console.error('Failed to persist job id:', e);
                }
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
                const response = await fetch(`${this.apiBase}/ingest/status/${this.currentJobId}`);

                const data = await response.json();

                this.updateStatusDisplay(data);

                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(this.statusCheckInterval);
                    this.statusCheckInterval = null;

                    // clear stored job id when job finishes
                    try {
                        localStorage.removeItem('rag_current_job_id');
                    } catch (e) {
                        console.error('Failed to clear job id from storage:', e);
                    }

                    if (data.status === 'completed') {
                        const pages = data.result.pages_indexed ?? data.result.pages_crawled ?? 0;
                        const chunks = data.result.chunks_indexed ?? 0;
                        this.addLogEntry(`🎉 Ingestion completed! ${pages} pages, ${chunks} chunks indexed.`, 'success');
                        this.loadCollections(); // Refresh collections list
                    } else {
                        this.addLogEntry(`❌ Ingestion failed: ${data.error}`, 'error');
                    }
                }
            } catch (error) {
                console.error('Status check error:', error);
                this.addLogEntry(`⚠️ Status check failed: ${error.message}`, 'warning');
            }
        }, 60000); // Check every 60 seconds
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

        // Update progress (detailed) with timestamp
        const now = new Date().toLocaleTimeString();

        if (data.progress) {
            const p = data.progress;

            const parts = [];

            if (p.message) {
                parts.push(p.message);
            }

            // numeric counters from backend progress
            parts.push(
                `Pages fetched: ${p.pages_fetched ?? 0}`,
                `Chunks extracted: ${p.chunks_extracted ?? 0}`,
                `Embeddings created: ${p.embeddings_created ?? 0}`,
                `Points upserted: ${p.points_upserted ?? 0}`
            );

            progressText.textContent = `[${now}] ` + parts.join(' | ');
        } else if (data.result) {
            // Fallback to final result summary if no incremental progress
            const pages = data.result.pages_indexed || data.result.pages_crawled || 0;
            const chunks = data.result.chunks_indexed || 0;
            progressText.textContent = `[${now}] Indexed: ${pages} pages, ${chunks} chunks`;
        } else {
            progressText.textContent = `[${now}] In progress...`;
        }
    }

    async loadCollections() {
        try {
            const collectionsList = document.getElementById('collections-list');
            const widgetCollectionSelect = document.getElementById('widget-collection');

            // Show loading state
            collectionsList.innerHTML = '<div class="collection-loading">Loading collections...</div>';
            widgetCollectionSelect.innerHTML = '<option value="">Loading collections...</option>';

            const response = await fetch(`${this.apiBase}/collections`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            // Clear existing
            collectionsList.innerHTML = '';
            widgetCollectionSelect.innerHTML = '';

            if (data.collections && data.collections.length > 0) {
                data.collections.forEach(collection => {
                    // Card in list
                    this.addCollectionCard(collection.name);

                    // Option in widget select
                    const option = document.createElement('option');
                    option.value = collection.name;
                    option.textContent = collection.name;
                    widgetCollectionSelect.appendChild(option);
                });

                // Ensure widget code reflects current selection
                this.updateWidgetCode();
            } else {
                collectionsList.innerHTML = '<div class="collection-loading">No collections found</div>';
                widgetCollectionSelect.innerHTML = '<option value="">No collections available</option>';
            }
        } catch (error) {
            console.error('Error loading collections:', error);
            document.getElementById('collections-list').innerHTML =
                '<div class="collection-loading">Error loading collections</div>';
            document.getElementById('widget-collection').innerHTML =
                '<option value="">Error loading collections</option>';
        }
    }

    async loadActiveProcesses() {
        try {
            const activeProcessesContainer = document.getElementById('active-processes-container');
            const activeProcessesList = document.getElementById('active-processes-list');

            // Show loading state
            activeProcessesList.innerHTML = '<div class="process-loading">Loading ingestion jobs...</div>';

            // Try active processes first, then recent jobs
            let response = await fetch(`${this.apiBase}/ingest/active`);
            let data;

            if (response.ok) {
                data = await response.json();
                if (!data.active_processes || data.active_processes.length === 0) {
                    // No active processes, try recent jobs
                    response = await fetch(`${this.apiBase}/ingest/jobs?limit=20`);
                    data = await response.json();
                    data.active_processes = data.jobs || [];
                }
            } else {
                // Fallback to recent jobs if active endpoint fails
                response = await fetch(`${this.apiBase}/ingest/jobs?limit=20`);
                data = await response.json();
                data.active_processes = data.jobs || [];
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Clear existing
            activeProcessesList.innerHTML = '';

            if (data.active_processes && data.active_processes.length > 0) {
                // Show container
                activeProcessesContainer.style.display = 'block';

                data.active_processes.forEach(process => {
                    this.addActiveProcessCard(process);
                });
            } else {
                activeProcessesList.innerHTML = '<div class="process-loading">No ingestion jobs found</div>';
                // Still show container but with empty message
                activeProcessesContainer.style.display = 'block';
            }
        } catch (error) {
            console.error('Error loading ingestion jobs:', error);
            document.getElementById('active-processes-list').innerHTML =
                '<div class="process-loading">Error loading ingestion jobs</div>';
            // Show container even on error
            document.getElementById('active-processes-container').style.display = 'block';
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

    addActiveProcessCard(process) {
        const activeProcessesList = document.getElementById('active-processes-list');

        const card = document.createElement('div');
        card.className = 'process-card';
        card.innerHTML = `
            <div class="process-header">
                <div class="process-collection">${process.collection}</div>
                <div class="process-status status-${process.status}">${this.capitalizeFirst(process.status)}</div>
            </div>
            <div class="process-details">
                <div class="process-url">🌐 ${process.url}</div>
                <div class="process-job-id">🆔 ${process.job_id || 'N/A'}</div>
                <div class="process-progress">
                    ${process.progress?.message || 'Processing...'}
                    ${process.progress?.pages_fetched ? ` (${process.progress.pages_fetched} pages)` : ''}
                </div>
                ${process.created_at ? `<div class="process-time">🕒 Started: ${new Date(process.created_at * 1000).toLocaleTimeString()}</div>` : ''}
            </div>
        `;

        activeProcessesList.appendChild(card);
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
        const color = document.getElementById('widget-color').value;
        const sendText = document.getElementById('widget-send-text').value;
        const placeholder = document.getElementById('widget-placeholder').value;

        const code = `<script>
window.AIWidgetConfig = {
  apiBase: '${this.apiBase}',
  collection: '${collection}',
  title: '${title}',
  language: 'en',
  welcomeMessage: '${message}',
  color: '${color}',
  sendButtonText: '${sendText}',
  inputPlaceholder: '${placeholder}'
};
</script>
<script src="http://localhost:8000/widget/widget.js"></script>`;

        document.getElementById('widget-code').textContent = code;

        // Also update live widget on this page, if it is loaded
        if (window.AIWidget && typeof window.AIWidget.init === 'function') {
            window.AIWidget.init({
                apiBase: this.apiBase,
                collection,
                title,
                language: 'en',
                welcomeMessage: message,
                color,
                sendText,
                placeholder
            });
        }
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
