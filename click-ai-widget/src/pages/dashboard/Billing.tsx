import { useState, useEffect } from "react";
import { tariffs, payments as paymentsApi } from "@/lib/api";
import { Check, ExternalLink } from "lucide-react";

interface Tariff {
  id: number;
  name: string;
  pages_limit: number;
  requests_limit: number;
  price_rub_month: number;
  description: string | null;
}

interface Payment {
  id: number;
  amount: number;
  tariff_name: string | null;
  status: string;
  created_at: string;
}

export default function Billing() {
  const [tariffList, setTariffList] = useState<Tariff[]>([]);
  const [paymentsList, setPaymentsList] = useState<Payment[]>([]);
  const [subscription, setSubscription] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      tariffs.list(),
      paymentsApi.list(),
      tariffs.mySubscription().catch(() => null),
    ])
      .then(([t, p, s]) => {
        setTariffList(t);
        setPaymentsList(p);
        setSubscription(s);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const ADMIN_LINK = "https://t.me/seomozg"; // Replace with actual admin contact

  function formatTariffName(name: string): string {
    const map: Record<string, string> = {
      free: "Free",
      tariff_100: "100 Pages",
      tariff_500: "500 Pages",
      tariff_1000: "1000 Pages",
    };
    return map[name] || name;
  }

  function formatPrice(price: number): string {
    if (price === 0) return "Free";
    return `${price.toLocaleString("ru-RU")} ₽/mo`;
  }

  if (loading) {
    return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Billing & Plans</h1>

      {error && <div className="mb-4 p-4 bg-red-50 text-red-600 rounded-lg">{error}</div>}

      {/* Current plan */}
      {subscription && (
        <div className="mb-6 p-5 bg-blue-50 rounded-xl border border-blue-100">
          <p className="text-sm text-blue-600 font-medium">Current Plan</p>
          <p className="text-xl font-bold text-blue-900 mt-1">{formatTariffName(subscription.tariff?.name)}</p>
          <p className="text-sm text-blue-600 mt-1">{subscription.tariff?.description}</p>
        </div>
      )}

      {/* Tariff grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {tariffList.map((tariff) => {
          const isCurrent = subscription?.tariff?.id === tariff.id;
          return (
            <div
              key={tariff.id}
              className={`bg-white rounded-xl shadow-sm border p-6 relative ${isCurrent ? "ring-2 ring-blue-500" : "border-gray-100"}`}
            >
              {isCurrent && (
                <span className="absolute top-3 right-3 bg-blue-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                  CURRENT
                </span>
              )}
              <h3 className="text-lg font-bold text-gray-900">{formatTariffName(tariff.name)}</h3>
              <p className="text-2xl font-extrabold text-gray-900 mt-2">{formatPrice(tariff.price_rub_month)}</p>
              <p className="text-xs text-gray-400 mt-1">{tariff.description}</p>
              <ul className="mt-4 space-y-2 text-sm text-gray-600">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                  {tariff.pages_limit} pages
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                  {tariff.requests_limit === -1 ? "Unlimited requests" : `${tariff.requests_limit} requests`}
                </li>
              </ul>
              {tariff.price_rub_month > 0 && (
                <button
                  disabled={isCurrent}
                  onClick={() => tariff.price_rub_month >= 10000
                    ? window.open(ADMIN_LINK, "_blank")
                    : null
                  }
                  className={`w-full mt-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    tariff.price_rub_month >= 10000
                      ? "bg-gray-900 text-white hover:bg-gray-800"
                      : "bg-gray-100 text-gray-400 cursor-not-allowed"
                  }`}
                >
                  {tariff.price_rub_month >= 10000
                    ? "Contact Admin"
                    : "Coming Soon"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Payment history */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="p-5 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Payment History</h2>
        </div>
        {paymentsList.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-gray-500 uppercase tracking-wider">
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3">Tariff</th>
                  <th className="px-5 py-3">Amount</th>
                  <th className="px-5 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {paymentsList.map((p) => (
                  <tr key={p.id} className="border-t border-gray-50">
                    <td className="px-5 py-3 text-sm text-gray-600">{new Date(p.created_at).toLocaleDateString("ru-RU")}</td>
                    <td className="px-5 py-3 text-sm">{p.tariff_name || "-"}</td>
                    <td className="px-5 py-3 text-sm font-medium">{p.amount.toLocaleString("ru-RU")} ₽</td>
                    <td className="px-5 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                        p.status === "succeeded" ? "bg-green-100 text-green-700" :
                        p.status === "pending" ? "bg-yellow-100 text-yellow-700" :
                        "bg-red-100 text-red-700"
                      }`}>
                        {p.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-gray-400">No payments yet</div>
        )}
      </div>
    </div>
  );
}