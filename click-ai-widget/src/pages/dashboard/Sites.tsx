import { useState, useEffect } from "react";
import { sites as sitesApi, ingest } from "@/lib/api";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Trash2, ExternalLink, Loader2 } from "lucide-react";

interface Site {
  id: number;
  collection_name: string;
  url: string;
  pages_indexed: number;
  deepseek_tokens: number;
  jina_tokens: number;
  chat_requests: number;
  created_at: string;
}

export default function Sites() {
  const [sitesList, setSitesList] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [adding, setAdding] = useState(false);
  const navigate = useNavigate();

  function loadSites() {
    setLoading(true);
    sitesApi.list()
      .then(setSitesList)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadSites(); }, []);

  async function handleAdd() {
    if (!newUrl.trim()) return;
    setAdding(true);
    setError("");
    try {
      const site = await sitesApi.create(newUrl.trim());
      try {
        const resp = await ingest.start(newUrl.trim(), site.collection_name);
        setError(`Парсинг запущен: задача ${resp.job_id || 'создана'}`);
      } catch (ingestErr: any) {
        setError(`Сайт добавлен, но парсинг не запустился: ${ingestErr.message}`);
      }
      setShowAdd(false);
      setNewUrl("");
      loadSites();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Удалить этот сайт? Данные из Qdrant не будут удалены.")) return;
    try {
      await sitesApi.delete(id);
      loadSites();
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (loading) {
    return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">Сайты</h1>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Добавить сайт
        </button>
      </div>

      {error && <div className="mb-4 p-4 bg-primary/10 text-foreground rounded-lg text-sm">{error}</div>}

      {showAdd && (
        <div className="mb-6 p-6 bg-card rounded-xl shadow-sm border border-border">
          <h2 className="text-lg font-semibold text-foreground mb-3">Добавить новый сайт</h2>
          <div className="flex gap-3">
            <input
              type="text"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              placeholder="https://example.com"
              className="flex-1 px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary bg-background text-foreground"
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            />
            <button
              onClick={handleAdd}
              disabled={adding || !newUrl.trim()}
              className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors text-sm font-medium flex items-center gap-2"
            >
              {adding && <Loader2 className="w-4 h-4 animate-spin" />}
              {adding ? "Добавление..." : "Добавить и индексировать"}
            </button>
          </div>
        </div>
      )}

      {sitesList.length > 0 ? (
        <div className="space-y-4">
          {sitesList.map((site) => (
            <div key={site.id} className="bg-card rounded-xl shadow-sm border border-border p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <Link to={`/dashboard/sites/${site.id}`} className="text-lg font-semibold text-primary hover:underline">
                    {site.collection_name}
                  </Link>
                  <p className="text-sm text-muted-foreground mt-0.5 flex items-center gap-1">
                    {site.url}
                    <a href={site.url.startsWith("http") ? site.url : `https://${site.url}`} target="_blank" rel="noreferrer" className="text-muted-foreground/50 hover:text-foreground">
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(site.id)}
                  className="p-2 text-muted-foreground hover:text-red-400 transition-colors"
                  title="Удалить сайт"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
                <div>
                  <p className="text-xs text-muted-foreground">Страниц</p>
                  <p className="text-sm font-semibold text-foreground">{site.pages_indexed}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Запросов</p>
                  <p className="text-sm font-semibold text-foreground">{site.chat_requests}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">DeepSeek</p>
                  <p className="text-sm font-semibold text-foreground">{site.deepseek_tokens.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Jina</p>
                  <p className="text-sm font-semibold text-foreground">{site.jina_tokens.toLocaleString()}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16">
          <p className="text-muted-foreground mb-4">Сайтов пока нет.</p>
          <button onClick={() => setShowAdd(true)} className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 text-sm">
            Добавить первый сайт
          </button>
        </div>
      )}
    </div>
  );
}