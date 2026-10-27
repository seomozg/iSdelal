import { motion } from "framer-motion";
import { FileText, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { useLanguage } from "@/contexts/LanguageContext";

/**
 * Documents feature banner shown right under the Telegram banner.
 * Static marketing block (no backend call) describing that PDF/Excel/
 * Google Docs and Sheets become part of the project's knowledge base.
 */
const DocsBanner = () => {
  const { t } = useLanguage();

  return (
    <section className="px-4 pt-2 pb-4">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="glass-card rounded-2xl p-6 sm:p-8 relative overflow-hidden border border-[#8B5CF6]/30"
        >
          {/* background accent */}
          <div className="absolute inset-0 bg-gradient-to-r from-[#8B5CF6]/10 via-transparent to-primary/10 pointer-events-none" />

          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center gap-6">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-[#8B5CF6]/15 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5 text-[#8B5CF6]" />
                </div>
                <span className="px-3 py-1 rounded-full bg-[#8B5CF6]/15 text-[#8B5CF6] text-xs font-semibold uppercase tracking-wider">
                  {t.docsBanner.badge}
                </span>
              </div>
              <h3 className="text-xl sm:text-2xl font-bold mb-2">
                {t.docsBanner.title}
              </h3>
              <p className="text-muted-foreground text-sm sm:text-base leading-relaxed mb-3">
                {t.docsBanner.subtitle}
              </p>
              <div className="flex flex-wrap gap-2">
                {t.docsBanner.formats.map((f) => (
                  <span
                    key={f}
                    className="px-2.5 py-1 rounded-md bg-[#8B5CF6]/10 text-[#8B5CF6] text-xs font-medium"
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>

            <Link
              to="/dashboard"
              className="shrink-0 inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-[#8B5CF6] text-white font-semibold hover:bg-[#7c50e8] hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 shadow-lg shadow-[#8B5CF6]/25"
            >
              {t.docsBanner.cta}
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default DocsBanner;
