import { useAuth } from "@/contexts/AuthContext";
import { useState, useEffect } from "react";
import { tariffs } from "@/lib/api";
import { Calendar, Mail, User as UserIcon } from "lucide-react";

export default function Profile() {
  const { user } = useAuth();
  const [subscription, setSubscription] = useState<any>(null);

  useEffect(() => {
    tariffs.mySubscription()
      .then(setSubscription)
      .catch(() => setSubscription(null));
  }, []);

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString("ru-RU", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-foreground mb-6">Профиль</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User info */}
        <div className="bg-card rounded-xl shadow-sm border border-border p-6 text-center">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="w-20 h-20 rounded-full mx-auto mb-4" />
          ) : (
            <div className="w-20 h-20 bg-secondary rounded-full flex items-center justify-center mx-auto mb-4">
              <UserIcon className="w-8 h-8 text-muted-foreground" />
            </div>
          )}
          <h2 className="text-xl font-bold text-foreground">{user?.name || "Пользователь"}</h2>
          <p className="text-muted-foreground text-sm mt-1 flex items-center justify-center gap-1">
            <Mail className="w-3 h-3" />
            {user?.email}
          </p>
          {user?.created_at && (
            <p className="text-muted-foreground text-xs mt-2 flex items-center justify-center gap-1">
              <Calendar className="w-3 h-3" />
              Участник с {formatDate(user.created_at)}
            </p>
          )}
        </div>

        {/* Subscription info */}
        <div className="lg:col-span-2 bg-card rounded-xl shadow-sm border border-border p-6">
          <h2 className="text-lg font-semibold text-foreground mb-4">Подписка</h2>
          {subscription ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-background rounded-lg">
                  <p className="text-xs text-muted-foreground">Тариф</p>
                  <p className="text-lg font-bold text-foreground">{subscription.tariff?.name || "Бесплатный"}</p>
                </div>
                <div className="p-4 bg-background rounded-lg">
                  <p className="text-xs text-muted-foreground">Статус</p>
                  <p className={`text-lg font-bold ${subscription.active ? "text-green-400" : "text-red-400"}`}>
                    {subscription.active ? "Активен" : "Неактивен"}
                  </p>
                </div>
                <div className="p-4 bg-background rounded-lg">
                  <p className="text-xs text-muted-foreground">Лимит страниц</p>
                  <p className="text-lg font-bold text-foreground">{subscription.tariff?.pages_limit || "-"}</p>
                </div>
                <div className="p-4 bg-background rounded-lg">
                  <p className="text-xs text-muted-foreground">Лимит запросов</p>
                  <p className="text-lg font-bold text-foreground">
                    {subscription.tariff?.requests_limit === -1 ? "Безлимит" : subscription.tariff?.requests_limit || "-"}
                  </p>
                </div>
              </div>
              <div className="p-4 bg-background rounded-lg">
                <p className="text-xs text-muted-foreground">С</p>
                <p className="text-sm font-medium text-foreground">{formatDate(subscription.created_at)}</p>
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground">Подписка не найдена.</p>
          )}
        </div>
      </div>
    </div>
  );
}