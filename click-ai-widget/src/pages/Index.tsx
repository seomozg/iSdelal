import { useState } from "react";
import Hero from "@/components/Hero";
import HowItWorks from "@/components/HowItWorks";
import WidgetCode from "@/components/WidgetCode";
import WidgetConfig from "@/components/WidgetConfig";
import Features from "@/components/Features";
import Pricing from "@/components/Pricing";
import FAQ from "@/components/FAQ";
import Footer from "@/components/Footer";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { LanguageProvider } from "@/contexts/LanguageContext";
import { toast } from "@/hooks/use-toast";

const IndexContent = () => {
  const [submittedUrl, setSubmittedUrl] = useState("");
  const [collectionName, setCollectionName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showWidgetCode, setShowWidgetCode] = useState(false);
  const [widgetConfig, setWidgetConfig] = useState({
    title: "AI Ассистент",
    welcomeMessage: "Привет! Чем я могу помочь?",
    sendButtonText: "Отправить",
    inputPlaceholder: "Задайте вопрос...",
    color: "#3B82F6",
  });

  const handleUrlSubmit = async (url: string) => {
    setIsLoading(true);

    try {
      // Generate collection name from URL domain
      const domainMatch = url.match(/^(?:https?:\/\/)?(?:www\.)?([^./]+)/);
      const collectionName = domainMatch ? domainMatch[1].replace(/[^a-zA-Z0-9]/g, '').toLowerCase() : 'default_collection';

      const requestBody = {
        url: url,
        collection: collectionName
      };

      const response = await fetch('/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'your-random-secret-key'
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('API Error:', response.status, errorText);
        throw new Error(`Failed to create agent (${response.status})`);
      }

      const data = await response.json();
      console.log('Ingest job created:', data.job_id);

      setSubmittedUrl(url);
      setCollectionName(collectionName);
      setShowWidgetCode(true);

      toast({
        title: "Agent Created!",
        description: "AI agent is being trained on your website. Embed code is ready.",
      });

    } catch (error) {
      console.error('Error creating agent:', error);
      toast({
        title: "Error",
        description: "Failed to create AI agent. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-background">
      <LanguageSwitcher />
      <Hero onSubmit={handleUrlSubmit} isLoading={isLoading} />
      <HowItWorks />
      <WidgetCode url={submittedUrl} isVisible={showWidgetCode} config={widgetConfig} collectionName={collectionName} />
      <WidgetConfig config={widgetConfig} onChange={setWidgetConfig} isVisible={showWidgetCode} />
      <Features />
      <Pricing />
      <FAQ />
      <Footer />
    </main>
  );
};

const Index = () => {
  return (
    <LanguageProvider>
      <IndexContent />
    </LanguageProvider>
  );
};

export default Index;
