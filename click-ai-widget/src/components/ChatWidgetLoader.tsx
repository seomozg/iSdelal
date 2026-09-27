import { useEffect } from "react";

const SCRIPT_ID = "ai-widget-script";

/**
 * Loads the demo chat widget (widget.js/widget.css are served by the backend
 * at /widget/*, which Vite cannot bundle from index.html). The config is set
 * right before the script is appended so the widget picks it up on init.
 */
const ChatWidgetLoader = () => {
  useEffect(() => {
    if (document.getElementById(SCRIPT_ID)) return;

    (window as unknown as Record<string, unknown>).AIWidgetConfig = {
      apiBase: window.location.origin,
      collection: "siteagent",
      title: "AI Assistant",
      language: "en",
      welcomeMessage: "Hello! How can I help you today?",
      color: "#3B82F6",
      sendButtonText: "Send",
      inputPlaceholder: "Type your message...",
    };

    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `${window.location.origin}/widget/widget.css?v=2`;
    document.head.appendChild(link);

    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.src = `${window.location.origin}/widget/widget.js?v=2`;
    document.body.appendChild(script);
  }, []);

  return null;
};

export default ChatWidgetLoader;
