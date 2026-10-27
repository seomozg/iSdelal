import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { sites as sitesApi, collections, bot, documents, SiteDocument } from "@/lib/api";
import { tgStartLink } from "@/lib/telegram";
import {
  ArrowLeft, Copy, Check, Code2, Settings, Send, ExternalLink,
  FileText, FileSpreadsheet, Loader2, Trash2, Link2, Upload,
} from "lucide-react";


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

/** Icon for a document row based on its source type. */
function DocIcon({ type }: { type: string }) {
  const Icon = type === "xlsx" || type === "google_sheet" ? FileSpreadsheet : FileText;
  return <Icon className="w-4 h-4 text-primary shrink-0" />;
}

export default function SiteDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [site, setSite] = useState<Site | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [tgCopied, setTgCopied] = useState(false);
  const [qdrantPoints, setQdrantPoints] = useState(0);
  const [botInfo, setBotInfo] = useState<{ enabled: boolean; username: string | null } | null>(null);

  // Document (knowledge base) state
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [docs, setDocs] = useState<SiteDocument[]>([]);
  const [docUploading, setDocUploading] = useState(false);
  const [docError, setDocError] = useState("");
  const [gUrl, setGUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

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

  useEffect(() => {
    bot.info().then(setBotInfo).catch(() => setBotInfo(null));
  }, []);

  function loadDocs() {
    if (!id) return;
    documents
      .list(parseInt(id))
      .then(setDocs)
      .catch(() => setDocError("Не удалось загрузить список документов"));
  }

  useEffect(() => {
    loadDocs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Poll the list while some document is still being processed.
  const hasProcessing = docs.some((d) => d.status === "processing");
  useEffect(() => {
    if (!hasProcessing) return;
    const timer = setInterval(loadDocs, 3000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasProcessing]);

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

  function getTgLink(): string {
    if (!site || !botInfo?.username) return "";
    return tgStartLink(botInfo.username, site.collection_name);
  }

  function handleCopyTg() {
    navigator.clipboard.writeText(getTgLink());
    setTgCopied(true);
    setTimeout(() => setTgCopied(false), 2000);
  }

  async function handleUploadFile() {
    if (!id || !selectedFile) return;
    setDocUploading(true);
    setDocError("");
    try {
      await documents.upload(parseInt(id), selectedFile);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      loadDocs();
    } catch (e) {
      setDocError(e instanceof Error ? e.message : "Ошибка загрузки файла");
    } finally {
      setDocUploading(false);
    }
  }

  async function handleAddUrl() {
    if (!id || !gUrl.trim()) return;
    setDocUploading(true);
    setDocError("");
    try {
      await documents.addUrl(parseInt(id), gUrl.trim());
      setGUrl("");
      loadDocs();
    } catch (e) {
      setDocError(e instanceof Error ? e.message : "Ошибка добавления ссылки");
    } finally {
      setDocUploading(false);
    }
  }

  async function handleDeleteDoc(doc: SiteDocument) {
    if (!id) return;
    if (!confirm(`Удалить документ «${doc.name}» из базы знаний?`)) return;
    setDocError("");
    try {
      await documents.delete(parseInt(id), doc.id);
      loadDocs();
    } catch (e) {
      setDocError(e instanceof Error ? e.message : "Ошибка удаления");
    }
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
                { label: "Чанков в Qdrant", value: qdrantPoints },
                { label: "Запросов в чат", value: site.chat_requests },
                { label: "DeepSeek токенов", value: site.deepseek_tokens.toLocaleString() },
                { label: "Jina токенов", value: site.jina_tokens.toLocaleString() },
              ].map(({ label, value }) => (
                <div key={label}>
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className="text-lg font-bold text-foreground">{value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Documents (knowledge base) */}
          <div className="bg-card rounded-xl shadow-sm border border-border p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                <FileText className="w-5 h-5" /> Документы
              </h2>
              <span className="text-xs text-muted-foreground">{docs.length} шт.</span>
            </div>
            <p className="text-xs text-muted-foreground mb-4">
              PDF, Excel, Google Docs и Google Sheets попадают в базу знаний проекта —
              ответы ИИ учитывают их наравне с сайтом.
            </p>

            <div className="flex gap-2 mb-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.xlsx"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                className="flex-1 text-xs text-muted-foreground file:mr-3 file:px-3 file:py-1.5 file:rounded-lg file:border-0 file:bg-primary/10 file:text-primary file:text-xs file:cursor-pointer"
              />
              <button
                onClick={handleUploadFile}
                disabled={docUploading || !selectedFile}
                className="flex items-center gap-1 px-3 py-2 bg-primary text-primary-foreground text-xs rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {docUploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
                Загрузить
              </button>
            </div>

            <div className="flex gap-2 mb-4">
              <input
                type="url"
                value={gUrl}
                onChange={(e) => setGUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAddUrl()}
                placeholder="https://docs.google.com/..."
                className="flex-1 px-3 py-2 border border-border rounded-lg text-xs bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <button
                onClick={handleAddUrl}
                disabled={docUploading || !gUrl.trim()}
                className="flex items-center gap-1 px-3 py-2 bg-primary text-primary-foreground text-xs rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                <Link2 className="w-3 h-3" /> Добавить
              </button>
            </div>

            {docError && (
              <div className="mb-3 p-2 bg-red-500/10 text-red-400 rounded-lg text-xs">{docError}</div>
            )}

            {docs.length === 0 ? (
              <p className="text-sm text-muted-foreground">Документов пока нет.</p>
            ) : (
              <div className="space-y-2">
                {docs.map((d) => (
                  <div
                    key={d.id}
                    className="flex items-center gap-3 p-2 rounded-lg border border-border bg-background/50"
                  >
                    <DocIcon type={d.source_type} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-foreground truncate" title={d.source_url || d.file_name || d.name}>
                        {d.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {d.status === "completed" && `✓ ${d.chunk_count} фрагментов`}
                        {d.status === "processing" && "⏳ обработка…"}
                        {d.status === "failed" && (
                          <span className="text-red-400" title={d.error || ""}>✕ ошибка</span>
                        )}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDeleteDoc(d)}
                      className="p-1.5 text-muted-foreground hover:text-red-400 transition-colors"
                      title="Удалить документ"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
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

          {/* Telegram bot deep link */}
          {botInfo?.enabled && botInfo.username && (
            <div className="bg-card rounded-xl shadow-sm border border-border p-5">
              <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <Send className="w-5 h-5 text-[#229ED9]" /> Telegram-бот
              </h2>
              <p className="text-sm text-muted-foreground mb-3">
                Ссылка-приглашение привязывает чат к этому проекту: бот будет отвечать на вопросы по его контенту.
              </p>
              <pre className="bg-[#0f1729] text-[#e2e8f0] p-3 rounded-lg text-xs overflow-x-auto border border-border mb-3 break-all whitespace-pre-wrap">{getTgLink()}</pre>
              <div className="flex gap-2">
                <button
                  onClick={handleCopyTg}
                  className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-primary text-primary-foreground text-xs rounded-lg hover:bg-primary/90 transition-colors"
                >
                  {tgCopied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  {tgCopied ? "Скопировано!" : "Копировать"}
                </button>
                <a
                  href={getTgLink()}
                  target="_blank"
                  rel="noreferrer"
                  className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-[#229ED9] text-white text-xs rounded-lg hover:bg-[#1e8fc9] transition-colors"
                >
                  <ExternalLink className="w-3 h-3" />
                  Открыть
                </a>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}