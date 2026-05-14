import { useLanguage } from "@/contexts/LanguageContext";
import { motion } from "framer-motion";

const LanguageSwitcher = () => {
  const { language, setLanguage } = useLanguage();

  return (
    <div className="fixed top-4 right-4 z-50">
      <div className="glass-card rounded-full p-1 flex gap-1">
        <button
          onClick={() => setLanguage("ru")}
          className={`relative px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            language === "ru" ? "text-primary-foreground" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {language === "ru" && (
            <motion.div
              layoutId="activeLang"
              className="absolute inset-0 bg-primary rounded-full"
              transition={{ type: "spring", duration: 0.4 }}
            />
          )}
          <span className="relative z-10">RU</span>
        </button>
        <button
          onClick={() => setLanguage("en")}
          className={`relative px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            language === "en" ? "text-primary-foreground" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {language === "en" && (
            <motion.div
              layoutId="activeLang"
              className="absolute inset-0 bg-primary rounded-full"
              transition={{ type: "spring", duration: 0.4 }}
            />
          )}
          <span className="relative z-10">EN</span>
        </button>
      </div>
    </div>
  );
};

export default LanguageSwitcher;
