import { useState, useEffect } from "react";
import { stats } from "@/lib/api";
import { BarChart3, MessageSquare, FileText, Coins, Globe } from "lucide-react";
import { Link } from "react-router-dom";

interface UserStats {
  total_deepseek_tokens: number;
  total_jina_tokens: number;
  total_chat_requests: number;
  total_pages_indexed: number;
  sites: Array<{
    site_id: number;
    collection_name: string;
    url: string;
    deepseek_tokens: number;
    jina_tokens: number;
    chat_requests: number;
  }>;
}

export default function Overview() {
  const [data, setData] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    stats.user()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  }

  if (error) {
    return <div className="p-4 bg-red-500/10 text-red-400 rounded-lg">{error}</div>;
  }

  const cards = [
    { label: "Чанков в индексе", value: data?.total_pages_indexed ?? 0, icon: FileText, color: "text-blue-500", bg: "bg-blue-500/10" },
    { label: "Запросов в чат", value: data?.total_chat_requests ?? 0, icon: MessageSquare, color: "text-green-500", bg: "bg-green-500/10" },
    { label: "DeepSeek токенов", value: (data?.total_deepseek_tokens ?? 0).toLocaleString(), icon: BarChart3, color: "text-purple-500", bg: "bg-purple-500/10" },
    { label: "Jina токенов", value: (data?.total_jina_tokens ?? 0).toLocaleString(), icon: Coins, color: "text-orange-500", bg: "bg-orange-500/10" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-foreground mb-6">Обзор</h1>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="bg-card rounded-xl p-5 shadow-sm border border-border">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center`}>
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{label}</p>
                <p className="text-xl font-bold text-foreground">{value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Sites table */}
      <div className="bg-card rounded-xl shadow-sm border border-border">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Ваши сайты</h2>
          <Link to="/dashboard/sites" className="text-sm text-primary hover:text-primary/80">Все сайты →</Link>
        </div>
        {data?.sites && data.sites.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-muted-foreground uppercase tracking-wider">
                  <th className="px-5 py-3">Сайт</th>
                  <th className="px-5 py-3">Запросов</th>
                  <th className="px-5 py-3">DeepSeek</th>
                  <th className="px-5 py-3">Jina</th>
                </tr>
              </thead>
              <tbody>
                {data.sites.slice(0, 5).map((site) => (
                  <tr key={site.site_id} className="border-t border-border hover:bg-secondary/50">
                    <td className="px-5 py-3">
                      <Link to={`/dashboard/sites/${site.site_id}`} className="text-primary hover:underline font-medium">
                        {site.collection_name}
                      </Link>
                      <p className="text-xs text-muted-foreground">{site.url}</p>
                    </td>
                    <td className="px-5 py-3 text-sm text-foreground">{site.chat_requests}</td>
                    <td className="px-5 py-3 text-sm text-foreground">{site.deepseek_tokens.toLocaleString()}</td>
                    <td className="px-5 py-3 text-sm text-foreground">{site.jina_tokens.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-muted-foreground">
            <Globe className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>Сайтов пока нет.</p>
            <Link to="/dashboard/sites" className="text-primary hover:underline text-sm">Добавить первый сайт →</Link>
          </div>
        )}
      </div>
    </div>
  );
}