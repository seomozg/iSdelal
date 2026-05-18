import { useState, useEffect } from "react";
import { tariffs, payments as paymentsApi } from "@/lib/api";
import { Check, Loader2 } from "lucide-react";

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
  const [payingTariff, setPayingTariff] = useState<string | null>(null);

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

  const ADMIN_LINK = "mailto:umklaidet@yandex.ru";

  function formatTariffName(name: string): string {
    const map: Record<string, string> = {
      free: "Бесплатный",
      tariff_100: "100 Страниц",
      tariff_500: "500 Страниц",
      tariff_1000: "1000 Страниц",
    };
    return map[name] || name;
  }

  function formatPrice(price: number): string {
    if (price === 0) return "0 ₽";
    return `${price.toLocaleString("ru-RU")} ₽/мес`;
  }

  async function handlePay(tariffName: string) {
    setPayingTariff(tariffName);
    setError("");
    try {
      const result = await paymentsApi.yookassa(tariffName);
      if (result.confirmation_url) {
        window.location.href = result.confirmation_url;
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setPayingTariff(null);
    }
  }

  if (loading) {
    return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-foreground mb-6">Тарифы и оплата</h1>

      {error && <div className="mb-4 p-4 bg-red-500/10 text-red-400 rounded-lg text-sm">{error}</div>}

      {/* Current plan */}
      {subscription && (
        <div className="mb-6 p-5 bg-primary/10 rounded-xl border border-primary/20">
          <p className="text-sm text-primary font-medium">Текущий тариф</p>
          <p className="text-xl font-bold text-foreground mt-1">{formatTariffName(subscription.tariff?.name)}</p>
          <p className="text-sm text-muted-foreground mt-1">{subscription.tariff?.description}</p>
        </div>
      )}

      {/* Tariff grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {tariffList.map((tariff) => {
          const isCurrent = subscription?.tariff?.id === tariff.id;
          return (
            <div
              key={tariff.id}
              className={`relative bg-card rounded-xl shadow-sm border p-6 ${isCurrent ? "ring-2 ring-primary border-primary" : "border-border"}`}
            >
              {isCurrent && (
                <span className="absolute top-3 right-3 bg-primary text-primary-foreground text-[10px] font-bold px-2 py-0.5 rounded-full">
                  ТЕКУЩИЙ
                </span>
              )}
              <h3 className="text-lg font-bold text-foreground">{formatTariffName(tariff.name)}</h3>
              <p className="text-2xl font-extrabold text-foreground mt-2">{formatPrice(tariff.price_rub_month)}</p>
              <p className="text-xs text-muted-foreground mt-1">{tariff.description}</p>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                  {tariff.pages_limit} страниц
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                  {tariff.requests_limit === -1 ? "Безлимит запросов" : `${tariff.requests_limit} запросов`}
                </li>
              </ul>
              {tariff.price_rub_month > 0 && (
                <button
                  disabled={isCurrent || payingTariff === tariff.name}
                  onClick={() => {
                    if (tariff.price_rub_month >= 10000) {
                      window.open(ADMIN_LINK, "_blank");
                    } else {
                      handlePay(tariff.name);
                    }
                  }}
                  className={`w-full mt-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2 ${
                    tariff.price_rub_month >= 10000
                      ? "bg-secondary text-foreground hover:bg-secondary/80"
                      : isCurrent
                        ? "bg-muted text-muted-foreground cursor-not-allowed"
                        : "bg-primary text-primary-foreground hover:bg-primary/90"
                  }`}
                >
                  {payingTariff === tariff.name && <Loader2 className="w-4 h-4 animate-spin" />}
                  {tariff.price_rub_month >= 10000
                    ? "Написать админу"
                    : isCurrent
                      ? "Активен"
                      : "Оплатить"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Payment history */}
      <div className="bg-card rounded-xl shadow-sm border border-border">
        <div className="p-5 border-b border-border">
          <h2 className="text-lg font-semibold text-foreground">История платежей</h2>
        </div>
        {paymentsList.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-muted-foreground uppercase tracking-wider">
                  <th className="px-5 py-3">Дата</th>
                  <th className="px-5 py-3">Тариф</th>
                  <th className="px-5 py-3">Сумма</th>
                  <th className="px-5 py-3">Статус</th>
                </tr>
              </thead>
              <tbody>
                {paymentsList.map((p) => (
                  <tr key={p.id} className="border-t border-border">
                    <td className="px-5 py-3 text-sm text-muted-foreground">{new Date(p.created_at).toLocaleDateString("ru-RU")}</td>
                    <td className="px-5 py-3 text-sm text-foreground">{p.tariff_name || "-"}</td>
                    <td className="px-5 py-3 text-sm font-medium text-foreground">{p.amount.toLocaleString("ru-RU")} ₽</td>
                    <td className="px-5 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                        p.status === "succeeded" ? "bg-green-500/10 text-green-400" :
                        p.status === "pending" ? "bg-yellow-500/10 text-yellow-400" :
                        "bg-red-500/10 text-red-400"
                      }`}>
                        {p.status === "succeeded" ? "Оплачен" : p.status === "pending" ? "Ожидает" : p.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-muted-foreground">Платежей пока нет</div>
        )}
      </div>
    </div>
  );
}