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
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Profile</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User info */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 text-center">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="w-20 h-20 rounded-full mx-auto mb-4" />
          ) : (
            <div className="w-20 h-20 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
              <UserIcon className="w-8 h-8 text-gray-400" />
            </div>
          )}
          <h2 className="text-xl font-bold text-gray-900">{user?.name || "User"}</h2>
          <p className="text-gray-500 text-sm mt-1 flex items-center justify-center gap-1">
            <Mail className="w-3 h-3" />
            {user?.email}
          </p>
          {user?.created_at && (
            <p className="text-gray-400 text-xs mt-2 flex items-center justify-center gap-1">
              <Calendar className="w-3 h-3" />
              Member since {formatDate(user.created_at)}
            </p>
          )}
        </div>

        {/* Subscription info */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Subscription</h2>
          {subscription ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-400">Plan</p>
                  <p className="text-lg font-bold">{subscription.tariff?.name || "Free"}</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-400">Status</p>
                  <p className={`text-lg font-bold ${subscription.active ? "text-green-600" : "text-red-600"}`}>
                    {subscription.active ? "Active" : "Inactive"}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-400">Pages Limit</p>
                  <p className="text-lg font-bold">{subscription.tariff?.pages_limit || "-"}</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-400">Requests Limit</p>
                  <p className="text-lg font-bold">
                    {subscription.tariff?.requests_limit === -1 ? "Unlimited" : subscription.tariff?.requests_limit || "-"}
                  </p>
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-400">Since</p>
                <p className="text-sm font-medium">{formatDate(subscription.created_at)}</p>
              </div>
            </div>
          ) : (
            <p className="text-gray-400">No subscription found.</p>
          )}
        </div>
      </div>
    </div>
  );
}