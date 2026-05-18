import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { sites as sitesApi, collections } from "@/lib/api";
import { ArrowLeft, Copy, Check, Code2, Settings } from "lucide-react";

interface Site {
  id: number;
  collection_name: string;
  url: string;
  widget_config: Record<string, string>;
  pages_indexed: number;
  deepseek_tokens: number;
  jina_tokens: number;
  chat_requests: number;
  created_at: string;
}

export default function SiteDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [site, setSite] = useState<Site | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [qdrantPoints, setQdrantPoints] = useState(0);

  const [config, setConfig] = useState({
    title: "AI Assistant",
    welcomeMessage: "Hello! How can I help you today?",
    color: "#3B82F6",
    sendText: "Send",
    placeholder: "Type your message...",
  });

  useEffect(() => {
    if (!id) return;
    sitesApi.get(parseInt(id))
      .then(async (data) => {
        setSite(data);
        if (data.widget_config) {
          setConfig((prev) => ({ ...prev, ...data.widget_config }));
        }
        try {
          const coll = await collections.get(data.collection_name);
          setQdrantPoints(coll.points_count || 0);
        } catch {}
        setLoading(false);
      })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, [id]);

  async function saveWidgetConfig() {
    if (!id) return;
    try {
      const updated = await sitesApi.updateWidget(parseInt(id), config);
      setSite(updated);
      setError("");
    } catch (e: any) {
      setError(e.message);
    }
  }

  function getWidgetCode() {
    if (!site) return "";
    return `<script>
window.AIWidgetConfig = {
  apiBase: '${window.location.origin}',
  collection: '${site.collection_name}',
  title: '${config.title}',
  welcomeMessage: '${config.welcomeMessage}',
  color: '${config.color}',
  sendText: '${config.sendText}',
  placeholder: '${config.placeholder}'
};
</script>
<script src="${window.location.origin}/widget/widget.js"></script>`;
  }

  function handleCopy() {
    navigator.clipboard.writeText(getWidgetCode());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (loading) {
    return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  }

  if (error && !site) {
    return <div className="p-4 bg-red-500/10 text-red-400 rounded-lg">{error}</div>;
  }

  if (!site) return null;

  const apiBase = window.location.origin;

  return (
    <div>
      <button onClick={() => navigate("/dashboard/sites")} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-4 h-4" /> Назад к сайтам
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{site.collection_name}</h1>
          <a href={site.url.startsWith("http") ? site.url : `https://${site.url}`} target="_blank" rel="noreferrer" className="text-sm text-muted-foreground hover:text-primary">{site.url}</a>
        </div>
      </div>

      {error && <div className="mb-4 p-3 bg-red-500/10 text-red-400 rounded-lg text-sm">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: stats + widget code */}
        <div className="lg:col-span-2 space-y-6">
          {/* Stats */}
          <div className="bg-card rounded-xl shadow-sm border border-border p-5">
            <h2 className="text-lg font-semibold text-foreground mb-4">Статистика</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { label: "Qdrant Points", value: qdrantPoints },
                { label: "Chat Requests", value: site.chat_requests },
                { label: "DeepSeek Tokens", value: site.deepseek_tokens.toLocaleString() },
                { label: "Jina Tokens", value: site.jina_tokens.toLocaleString() },
              ].map(({ label, value }) => (
                <div key={label}>
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className="text-lg font-bold text-foreground">{value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Widget Code */}
          <div className="bg-card rounded-xl shadow-sm border border-border p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-foreground flex items-center gap-2"><Code2 className="w-5 h-5" /> Код виджета</h2>
              <button onClick={handleCopy} className="flex items-center gap-1 px-3 py-1.5 bg-primary text-primary-foreground text-xs rounded-lg hover:bg-primary/90 transition-colors">
                {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                {copied ? "Скопировано!" : "Копировать"}
              </button>
            </div>
            <pre className="bg-[#0f1729] text-[#e2e8f0] p-4 rounded-lg text-xs overflow-x-auto border border-border">{getWidgetCode()}</pre>
          </div>
        </div>

        {/* Right column: widget config */}
        <div className="space-y-6">
          <div className="bg-card rounded-xl shadow-sm border border-border p-5">
            <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2"><Settings className="w-5 h-5" /> Настройки виджета</h2>
            <div className="space-y-4">
              {[
                { key: "title", label: "Заголовок" },
                { key: "welcomeMessage", label: "Приветствие" },
                { key: "sendText", label: "Текст кнопки" },
                { key: "placeholder", label: "Placeholder" },
              ].map(({ key, label }) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">{label}</label>
                  <input
                    type="text"
                    value={config[key as keyof typeof config]}
                    onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
                    className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary bg-background text-foreground"
                  />
                </div>
              ))}
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Цвет</label>
                <input
                  type="color"
                  value={config.color}
                  onChange={(e) => setConfig({ ...config, color: e.target.value })}
                  className="w-full h-10 rounded-lg cursor-pointer border border-border"
                />
              </div>
              <button
                onClick={saveWidgetConfig}
                className="w-full py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium"
              >
                Сохранить
              </button>
            </div>
          </div>

          {/* API endpoints */}
          <div className="bg-card rounded-xl shadow-sm border border-border p-5">
            <h3 className="text-sm font-semibold text-foreground mb-2">API Endpoints</h3>
            <div className="space-y-1 text-xs text-muted-foreground font-mono">
              <p>POST {apiBase}/chat</p>
              <p>POST {apiBase}/chat/stream</p>
              <p>GET {apiBase}/collections/{site.collection_name}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}