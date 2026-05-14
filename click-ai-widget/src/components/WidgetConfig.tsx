import { motion } from "framer-motion";
import { Settings, MessageSquare, Send, Type, Palette } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

interface WidgetConfigProps {
  config: {
    title: string;
    welcomeMessage: string;
    sendButtonText: string;
    inputPlaceholder: string;
    color: string;
  };
  onChange: (config: WidgetConfigProps["config"]) => void;
  isVisible: boolean;
}

const colorPresets = [
  { name: "Blue", value: "#3B82F6" },
  { name: "Purple", value: "#8B5CF6" },
  { name: "Green", value: "#10B981" },
  { name: "Red", value: "#EF4444" },
  { name: "Orange", value: "#F97316" },
  { name: "Pink", value: "#EC4899" },
  { name: "Cyan", value: "#06B6D4" },
  { name: "Indigo", value: "#6366F1" },
];

const WidgetConfig = ({ config, onChange, isVisible }: WidgetConfigProps) => {
  const { t } = useLanguage();

  if (!isVisible) return null;

  const handleChange = (key: keyof typeof config, value: string) => {
    onChange({ ...config, [key]: value });
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut", delay: 0.2 }}
      className="py-16 px-4"
    >
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass-card mb-4">
            <Settings className="w-4 h-4 text-primary" />
            <span className="text-sm text-muted-foreground">{t.widgetConfig.title}</span>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-6">
          <div className="grid gap-6">
            {/* Widget Title */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Type className="w-4 h-4 text-primary" />
                {t.widgetConfig.widgetTitle}
              </label>
              <input
                type="text"
                value={config.title}
                onChange={(e) => handleChange("title", e.target.value)}
                placeholder="AI Assistant"
                className="w-full h-12 px-4 rounded-xl bg-secondary/80 border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            {/* Welcome Message */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-foreground">
                <MessageSquare className="w-4 h-4 text-primary" />
                {t.widgetConfig.welcomeMessage}
              </label>
              <textarea
                value={config.welcomeMessage}
                onChange={(e) => handleChange("welcomeMessage", e.target.value)}
                placeholder="Hello! How can I help you today?"
                rows={3}
                className="w-full px-4 py-3 rounded-xl bg-secondary/80 border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all resize-none"
              />
            </div>

            {/* Send Button Text */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Send className="w-4 h-4 text-primary" />
                {t.widgetConfig.sendButtonText}
              </label>
              <input
                type="text"
                value={config.sendButtonText}
                onChange={(e) => handleChange("sendButtonText", e.target.value)}
                placeholder="Send"
                className="w-full h-12 px-4 rounded-xl bg-secondary/80 border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            {/* Input Placeholder */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Type className="w-4 h-4 text-primary" />
                {t.widgetConfig.inputPlaceholder}
              </label>
              <input
                type="text"
                value={config.inputPlaceholder}
                onChange={(e) => handleChange("inputPlaceholder", e.target.value)}
                placeholder="Type your message..."
                className="w-full h-12 px-4 rounded-xl bg-secondary/80 border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              />
            </div>

            {/* Widget Color */}
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Palette className="w-4 h-4 text-primary" />
                {t.widgetConfig.widgetColor}
              </label>
              <div className="flex flex-wrap gap-3">
                {colorPresets.map((color) => (
                  <button
                    key={color.value}
                    onClick={() => handleChange("color", color.value)}
                    className={`w-10 h-10 rounded-full transition-all duration-200 ${
                      config.color === color.value
                        ? "ring-2 ring-offset-2 ring-offset-background ring-foreground scale-110"
                        : "hover:scale-105"
                    }`}
                    style={{ backgroundColor: color.value }}
                    title={color.name}
                  />
                ))}
                {/* Custom color input */}
                <div className="relative">
                  <input
                    type="color"
                    value={config.color}
                    onChange={(e) => handleChange("color", e.target.value)}
                    className="w-10 h-10 rounded-full cursor-pointer opacity-0 absolute inset-0"
                  />
                  <div
                    className="w-10 h-10 rounded-full border-2 border-dashed border-border flex items-center justify-center text-muted-foreground hover:border-primary hover:text-primary transition-colors"
                    style={
                      !colorPresets.find((c) => c.value === config.color)
                        ? { backgroundColor: config.color, borderStyle: "solid" }
                        : {}
                    }
                  >
                    {colorPresets.find((c) => c.value === config.color) && "+"}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Preview */}
          <div className="mt-8 pt-6 border-t border-border">
            <div className="flex justify-end">
              <div
                className="w-14 h-14 rounded-full flex items-center justify-center shadow-lg cursor-pointer transition-transform hover:scale-110"
                style={{ backgroundColor: config.color }}
              >
                <MessageSquare className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.section>
  );
};

export default WidgetConfig;
