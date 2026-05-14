import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Copy, Check, Code2, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/contexts/LanguageContext";

interface WidgetConfig {
  title: string;
  welcomeMessage: string;
  sendButtonText: string;
  inputPlaceholder: string;
  color: string;
}

interface WidgetCodeProps {
  url: string;
  isVisible: boolean;
  config: WidgetConfig;
  collectionName: string;
}

const WidgetCode = ({ url, isVisible, config, collectionName }: WidgetCodeProps) => {
  const [copied, setCopied] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);
  const { t } = useLanguage();



  const widgetCode = `<script>
window.AIWidgetConfig = {
  apiBase: window.location.origin,
  collection: '${collectionName}',
  title: '${config.title}',
  language: 'en',
  welcomeMessage: '${config.welcomeMessage}',
  color: '${config.color}',
  sendButtonText: '${config.sendButtonText}',
  inputPlaceholder: '${config.inputPlaceholder}'
};
</script>
<script src="${window.location.origin}/widget/widget.js"></script>`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(widgetCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  useEffect(() => {
    if (isVisible && sectionRef.current) {
      setTimeout(() => {
        sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 100);
    }
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <motion.section
      ref={sectionRef}
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="py-24 px-4"
    >
      <div className="max-w-3xl mx-auto">
        {/* Success indicator */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.5, delay: 0.2, type: "spring" }}
          className="flex justify-center mb-8"
        >
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center glow-lg">
            <Check className="w-10 h-10 text-primary-foreground" />
          </div>
        </motion.div>

        {/* Header */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-center mb-8"
        >
          <h2 className="text-3xl sm:text-4xl font-bold mb-3">
            {t.widgetCode.ready} <span className="gradient-text">{t.widgetCode.readyHighlight}</span>
          </h2>
          <p className="text-muted-foreground text-lg">
            {t.widgetCode.copyInstructions}
          </p>
        </motion.div>

        {/* Code block */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card rounded-2xl p-6 relative overflow-hidden"
        >
          {/* Decorative gradient */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary via-accent to-primary" />
          
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Code2 className="w-5 h-5 text-primary" />
              <span className="font-semibold">{t.widgetCode.codeTitle}</span>
            </div>
            <Button
              onClick={handleCopy}
              variant="glass"
              size="sm"
              className="gap-2"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-green-400" />
                  <span className="text-green-400">{t.widgetCode.copied}</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  {t.widgetCode.copy}
                </>
              )}
            </Button>
          </div>

          {/* Code display */}
          <div className="code-block text-sm sm:text-base overflow-x-auto">
            <code className="break-all">{widgetCode}</code>
          </div>

          {/* Instructions */}
          <div className="mt-4 flex items-start gap-3 p-4 rounded-xl bg-secondary/50 border border-border/50">
            <Info className="w-5 h-5 text-primary mt-0.5 shrink-0" />
            <p className="text-sm text-muted-foreground">
              {t.widgetCode.instructions} <code className="text-primary">&lt;/body&gt;</code> вашего сайта.
            </p>
          </div>
        </motion.div>

        {/* Website preview */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-6 text-center text-sm text-muted-foreground"
        >
          {t.widgetCode.configuredFor} <span className="text-foreground font-medium">{url}</span>
        </motion.div>
      </div>
    </motion.section>
  );
};

export default WidgetCode;
