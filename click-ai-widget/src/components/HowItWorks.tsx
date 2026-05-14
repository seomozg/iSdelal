import { motion } from "framer-motion";
import { Globe, Database, Code, Rocket } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

const icons = [Globe, Database, Code, Rocket];
const colors = [
  "from-cyan-400 to-blue-500",
  "from-blue-500 to-purple-500",
  "from-purple-500 to-pink-500",
  "from-pink-500 to-orange-400",
];

const HowItWorks = () => {
  const { t } = useLanguage();

  return (
    <section className="py-24 px-4 relative">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4">
            {t.howItWorks.title.split(" ").slice(0, -1).join(" ")}{" "}
            <span className="gradient-text">{t.howItWorks.title.split(" ").slice(-1)}</span>
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            {t.howItWorks.subtitle}
          </p>
        </motion.div>

        {/* Steps grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {t.howItWorks.steps.map((step, index) => {
            const Icon = icons[index];
            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="relative group"
              >
                {/* Connector line */}
                {index < t.howItWorks.steps.length - 1 && (
                  <div className="hidden lg:block absolute top-16 left-full w-full h-px bg-gradient-to-r from-border to-transparent z-0" />
                )}
                
                <div className="glass-card rounded-2xl p-6 h-full hover:border-primary/30 transition-all duration-300 relative z-10">
                  {/* Step number */}
                  <div className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-secondary border border-border flex items-center justify-center text-sm font-bold text-muted-foreground">
                    {index + 1}
                  </div>
                  
                  {/* Icon */}
                  <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${colors[index]} p-0.5 mb-5 group-hover:scale-110 transition-transform duration-300`}>
                    <div className="w-full h-full rounded-xl bg-card flex items-center justify-center">
                      <Icon className="w-6 h-6 text-foreground" />
                    </div>
                  </div>
                  
                  {/* Content */}
                  <h3 className="text-xl font-semibold mb-2">{step.title}</h3>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
