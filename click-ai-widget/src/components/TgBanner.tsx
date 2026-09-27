import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Send, ArrowRight } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { bot } from "@/lib/api";
import { tgLink } from "@/lib/telegram";

/**
 * Telegram bot banner shown right under the Hero.
 * Renders only when the backend reports a running bot with a username,
 * so there are never broken t.me links.
 */
const TgBanner = () => {
  const { t } = useLanguage();
  const [username, setUsername] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    bot
      .info()
      .then((info) => {
        if (!cancelled && info.enabled && info.username) {
          setUsername(info.username);
        }
      })
      .catch(() => {
        /* backend unavailable — hide the banner silently */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!username) return null;

  return (
    <section className="px-4 pt-4 pb-2">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="glass-card rounded-2xl p-6 sm:p-8 relative overflow-hidden border border-[#229ED9]/30"
        >
          {/* background accent */}
          <div className="absolute inset-0 bg-gradient-to-r from-[#229ED9]/10 via-transparent to-primary/10 pointer-events-none" />

          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center gap-6">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-[#229ED9]/15 flex items-center justify-center shrink-0">
                  <Send className="w-5 h-5 text-[#229ED9]" />
                </div>
                <span className="px-3 py-1 rounded-full bg-[#229ED9]/15 text-[#229ED9] text-xs font-semibold uppercase tracking-wider">
                  {t.tgBanner.badge}
                </span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold mb-2">
                {t.tgBanner.title}
              </h3>
              <p className="text-muted-foreground text-sm sm:text-base leading-relaxed">
                {t.tgBanner.subtitle}
              </p>
            </div>

            <a
              href={tgLink(username)}
              target="_blank"
              rel="noreferrer"
              className="shrink-0 inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-[#229ED9] text-white font-semibold hover:bg-[#1e8fc9] hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 shadow-lg shadow-[#229ED9]/25"
            >
              {t.tgBanner.cta}
              <ArrowRight className="w-4 h-4" />
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default TgBanner;
