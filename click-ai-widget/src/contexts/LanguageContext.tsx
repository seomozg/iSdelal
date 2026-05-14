import { createContext, useContext, useState, ReactNode } from "react";

type Language = "ru" | "en";

interface Translations {
  hero: {
    badge: string;
    title1: string;
    title2: string;
    subtitle: string;
    placeholder: string;
    button: string;
    loading: string;
    trust1: string;
    trust2: string;
    trust3: string;
  };
  howItWorks: {
    title: string;
    subtitle: string;
    steps: { title: string; description: string }[];
  };
  widgetCode: {
    ready: string;
    readyHighlight: string;
    copyInstructions: string;
    codeTitle: string;
    copy: string;
    copied: string;
    instructions: string;
    configuredFor: string;
  };
  widgetConfig: {
    title: string;
    widgetTitle: string;
    welcomeMessage: string;
    sendButtonText: string;
    inputPlaceholder: string;
    widgetColor: string;
  };
  features: {
    title: string;
    subtitle: string;
    items: { title: string; description: string }[];
  };
  faq: {
    title: string;
    subtitle: string;
    items: { question: string; answer: string }[];
  };
  footer: {
    description: string;
    product: string;
    features: string;
    pricing: string;
    docs: string;
    company: string;
    about: string;
    blog: string;
    careers: string;
    legal: string;
    privacy: string;
    terms: string;
    cookies: string;
    rights: string;
  };
}

const translations: Record<Language, Translations> = {
  ru: {
    hero: {
      badge: "На базе продвинутого ИИ",
      title1: "ИИ-агент для вашего сайта",
      title2: "в 1 клик!",
      subtitle: "Мгновенно добавьте умного контекстного помощника, обученного на контенте вашего сайта. Без программирования.",
      placeholder: "https://ваш-сайт.ru",
      button: "Создать агента",
      loading: "Обработка...",
      trust1: "Без банковской карты",
      trust2: "Настройка за 60 секунд",
      trust3: "Бесплатный тариф",
    },
    howItWorks: {
      title: "Как это работает",
      subtitle: "Четыре простых шага до вашего персонального ИИ-помощника",
      steps: [
        { title: "Введите URL", description: "Укажите адрес вашего сайта" },
        { title: "Индексация", description: "Мы сканируем и обучаем ИИ на контенте" },
        { title: "Скопируйте код", description: "Получите готовый код виджета" },
        { title: "Запуск!", description: "Виджет отвечает на вопросы посетителей" },
      ],
    },
    widgetCode: {
      ready: "Ваш ИИ-агент",
      readyHighlight: "готов!",
      copyInstructions: "Скопируйте и вставьте этот код на ваш сайт",
      codeTitle: "Код виджета",
      copy: "Копировать",
      copied: "Скопировано!",
      instructions: "Вставьте этот код перед закрывающим тегом",
      configuredFor: "Агент настроен для:",
    },
    widgetConfig: {
      title: "Настройка виджета",
      widgetTitle: "Заголовок виджета",
      welcomeMessage: "Приветственное сообщение",
      sendButtonText: "Текст кнопки отправки",
      inputPlaceholder: "Плейсхолдер поля ввода",
      widgetColor: "Цвет виджета",
    },
    features: {
      title: "Почему выбирают нас",
      subtitle: "Всё, что нужно для идеального клиентского сервиса",
      items: [
        { title: "Без обучения", description: "ИИ автоматически учится на контенте вашего сайта" },
        { title: "Контекстные ответы", description: "Релевантные ответы с первой минуты работы" },
        { title: "Быстрая интеграция", description: "Установка виджета занимает несколько секунд" },
        { title: "Безопасность", description: "Ваши данные защищены и масштабируемы" },
      ],
    },
    faq: {
      title: "Частые вопросы",
      subtitle: "Ответы на популярные вопросы о нашем сервисе",
      items: [
        { question: "Сколько времени занимает индексация?", answer: "Обычно индексация занимает от 1 до 5 минут в зависимости от размера сайта." },
        { question: "Мои данные в безопасности?", answer: "Да, мы используем шифрование и не передаём данные третьим лицам." },
        { question: "Можно ли настроить внешний вид виджета?", answer: "Да, вы можете изменить цвета, текст и позицию виджета." },
        { question: "Есть ли бесплатный тариф?", answer: "Да, мы предлагаем бесплатный тариф с базовыми функциями." },
      ],
    },
    footer: {
      description: "Умный ИИ-помощник для вашего сайта за считанные минуты.",
      product: "Продукт",
      features: "Возможности",
      pricing: "Цены",
      docs: "Документация",
      company: "Компания",
      about: "О нас",
      blog: "Блог",
      careers: "Карьера",
      legal: "Правовая информация",
      privacy: "Политика конфиденциальности",
      terms: "Условия использования",
      cookies: "Cookie",
      rights: "Все права защищены.",
    },
  },
  en: {
    hero: {
      badge: "Powered by Advanced AI",
      title1: "AI Agent for Your Website",
      title2: "in 1 Click!",
      subtitle: "Instantly add a smart, context-aware assistant trained on your own website's content. No coding required.",
      placeholder: "https://your-website.com",
      button: "Generate Agent",
      loading: "Processing...",
      trust1: "No credit card required",
      trust2: "Setup in 60 seconds",
      trust3: "Free tier available",
    },
    howItWorks: {
      title: "How It Works",
      subtitle: "Four simple steps to your personal AI assistant",
      steps: [
        { title: "Enter URL", description: "Provide your website address" },
        { title: "We Index & Train", description: "We scan and train AI on your content" },
        { title: "Copy Code", description: "Get your ready-to-use widget code" },
        { title: "Go Live!", description: "Widget answers visitor questions" },
      ],
    },
    widgetCode: {
      ready: "Your AI Agent is",
      readyHighlight: "Ready!",
      copyInstructions: "Copy and paste this code on your website",
      codeTitle: "Widget Code",
      copy: "Copy",
      copied: "Copied!",
      instructions: "Paste this code before the closing",
      configuredFor: "Agent configured for:",
    },
    widgetConfig: {
      title: "Widget Configuration",
      widgetTitle: "Widget Title",
      welcomeMessage: "Welcome Message",
      sendButtonText: "Send Button Text",
      inputPlaceholder: "Input Placeholder",
      widgetColor: "Widget Color",
    },
    features: {
      title: "Why Choose Us",
      subtitle: "Everything you need for perfect customer service",
      items: [
        { title: "Zero Training", description: "AI automatically learns from your website content" },
        { title: "Context-Aware", description: "Relevant answers from minute one" },
        { title: "Quick Integration", description: "Widget installation takes seconds" },
        { title: "Secure & Scalable", description: "Your data is protected and scalable" },
      ],
    },
    faq: {
      title: "FAQ",
      subtitle: "Answers to common questions about our service",
      items: [
        { question: "How long does indexing take?", answer: "Usually indexing takes 1-5 minutes depending on site size." },
        { question: "Is my data secure?", answer: "Yes, we use encryption and don't share data with third parties." },
        { question: "Can I customize the widget appearance?", answer: "Yes, you can change colors, text, and widget position." },
        { question: "Is there a free tier?", answer: "Yes, we offer a free tier with basic features." },
      ],
    },
    footer: {
      description: "Smart AI assistant for your website in minutes.",
      product: "Product",
      features: "Features",
      pricing: "Pricing",
      docs: "Documentation",
      company: "Company",
      about: "About",
      blog: "Blog",
      careers: "Careers",
      legal: "Legal",
      privacy: "Privacy Policy",
      terms: "Terms of Service",
      cookies: "Cookies",
      rights: "All rights reserved.",
    },
  },
};

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: Translations;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider = ({ children }: { children: ReactNode }) => {
  const [language, setLanguage] = useState<Language>("ru");

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t: translations[language] }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
};
