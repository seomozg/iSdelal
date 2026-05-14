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
    return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;
  }

  if (error) {
    return <div className="p-4 bg-red-50 text-red-600 rounded-lg">{error}</div>;
  }

  const cards = [
    { label: "Pages Indexed", value: data?.total_pages_indexed ?? 0, icon: FileText, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Chat Requests", value: data?.total_chat_requests ?? 0, icon: MessageSquare, color: "text-green-600", bg: "bg-green-50" },
    { label: "DeepSeek Tokens", value: (data?.total_deepseek_tokens ?? 0).toLocaleString(), icon: BarChart3, color: "text-purple-600", bg: "bg-purple-50" },
    { label: "Jina Tokens", value: (data?.total_jina_tokens ?? 0).toLocaleString(), icon: Coins, color: "text-orange-600", bg: "bg-orange-50" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard Overview</h1>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center`}>
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <div>
                <p className="text-sm text-gray-500">{label}</p>
                <p className="text-xl font-bold text-gray-900">{value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Sites table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="p-5 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Your Sites</h2>
          <Link to="/dashboard/sites" className="text-sm text-blue-600 hover:text-blue-700">View all →</Link>
        </div>
        {data?.sites && data.sites.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                  <th className="px-5 py-3">Site</th>
                  <th className="px-5 py-3">Chat Requests</th>
                  <th className="px-5 py-3">DeepSeek</th>
                  <th className="px-5 py-3">Jina</th>
                </tr>
              </thead>
              <tbody>
                {data.sites.slice(0, 5).map((site) => (
                  <tr key={site.site_id} className="border-t border-gray-50 hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <Link to={`/dashboard/sites/${site.site_id}`} className="text-blue-600 hover:underline font-medium">
                        {site.collection_name}
                      </Link>
                      <p className="text-xs text-gray-400">{site.url}</p>
                    </td>
                    <td className="px-5 py-3 text-sm">{site.chat_requests}</td>
                    <td className="px-5 py-3 text-sm">{site.deepseek_tokens.toLocaleString()}</td>
                    <td className="px-5 py-3 text-sm">{site.jina_tokens.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-gray-400">
            <Globe className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No sites yet.</p>
            <Link to="/dashboard/sites" className="text-blue-600 hover:underline text-sm">Add your first site →</Link>
          </div>
        )}
      </div>
    </div>
  );
}