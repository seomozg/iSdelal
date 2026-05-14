import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

interface TariffCard {
  name: string;
  nameRu: string;
  price: string;
  priceRu: string;
  pages: number;
  requests: string;
  requestsRu: string;
  description: string;
  descriptionRu: string;
  highlight: boolean;
  cta: string;
  ctaRu: string;
  isContact?: boolean;
}

const tariffs: TariffCard[] = [
  {
    name: "Free",
    nameRu: "Бесплатный",
    price: "0 ₽",
    priceRu: "0 ₽",
    pages: 10,
    requests: "100 requests",
    requestsRu: "100 запросов",
    description: "First 10 pages and 100 requests free",
    descriptionRu: "Первые 10 страниц и 100 запросов бесплатно",
    highlight: false,
    cta: "Get Started",
    ctaRu: "Начать",
  },
  {
    name: "100 Pages",
    nameRu: "100 Страниц",
    price: "1 000 ₽/mo",
    priceRu: "1 000 ₽/мес",
    pages: 100,
    requests: "Unlimited",
    requestsRu: "Безлимит",
    description: "100 pages, unlimited requests",
    descriptionRu: "100 страниц, безлимитные запросы",
    highlight: true,
    cta: "Popular",
    ctaRu: "Популярный",
  },
  {
    name: "500 Pages",
    nameRu: "500 Страниц",
    price: "5 000 ₽/mo",
    priceRu: "5 000 ₽/мес",
    pages: 500,
    requests: "Unlimited",
    requestsRu: "Безлимит",
    description: "500 pages, unlimited requests",
    descriptionRu: "500 страниц, безлимитные запросы",
    highlight: false,
    cta: "Choose",
    ctaRu: "Выбрать",
  },
  {
    name: "1000+ Pages",
    nameRu: "1000+ Страниц",
    price: "10 000 ₽/mo",
    priceRu: "10 000 ₽/мес",
    pages: 1000,
    requests: "Unlimited",
    requestsRu: "Безлимит",
    description: "1000 pages, unlimited requests",
    descriptionRu: "1000 страниц, безлимитные запросы",
    highlight: false,
    cta: "Contact Admin",
    ctaRu: "Написать админу",
    isContact: true,
  },
];

const ADMIN_LINK = "https://t.me/seomozg"; // Replace with actual admin contact

const Pricing = () => {
  const { language } = useLanguage();
  const isRu = language === "ru";

  return (
    <section className="py-20 px-4 bg-gray-50">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            {isRu ? "Тарифы" : "Plans & Pricing"}
          </h2>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto">
            {isRu
              ? "Выберите подходящий тариф. Первые 10 страниц и 100 запросов — бесплатно."
              : "Choose the right plan. First 10 pages and 100 requests are free."}
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {tariffs.map((tariff, i) => (
            <motion.div
              key={tariff.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className={`relative bg-white rounded-2xl p-6 shadow-sm border ${
                tariff.highlight
                  ? "ring-2 ring-blue-500 border-blue-500"
                  : "border-gray-100"
              }`}
            >
              {tariff.highlight && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                  {isRu ? tariff.ctaRu : tariff.cta}
                </span>
              )}

              <h3 className="text-lg font-bold text-gray-900 mt-2">
                {isRu ? tariff.nameRu : tariff.name}
              </h3>
              <p className="text-2xl font-extrabold text-gray-900 mt-2">
                {isRu ? tariff.priceRu : tariff.price}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {isRu ? tariff.descriptionRu : tariff.description}
              </p>

              <ul className="mt-5 space-y-2.5">
                <li className="flex items-start gap-2 text-sm text-gray-600">
                  <Check className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                  <span>
                    {tariff.pages} {isRu ? "страниц" : "pages"}
                  </span>
                </li>
                <li className="flex items-start gap-2 text-sm text-gray-600">
                  <Check className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                  <span>
                    {isRu ? tariff.requestsRu : tariff.requests}
                  </span>
                </li>
              </ul>

              {tariff.isContact ? (
                <a
                  href={ADMIN_LINK}
                  target="_blank"
                  rel="noreferrer"
                  className="block w-full mt-5 py-2.5 text-center text-sm font-medium bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
                >
                  {isRu ? tariff.ctaRu : tariff.cta}
                </a>
              ) : tariff.highlight ? (
                <a
                  href="/login"
                  className="block w-full mt-5 py-2.5 text-center text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  {isRu ? "Начать бесплатно" : "Start Free"}
                </a>
              ) : (
                <a
                  href="/login"
                  className="block w-full mt-5 py-2.5 text-center text-sm font-medium bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  {isRu ? "Начать бесплатно" : "Start Free"}
                </a>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Pricing;