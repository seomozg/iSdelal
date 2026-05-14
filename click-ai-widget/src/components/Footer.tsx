const Footer = () => {
  return (
    <footer className="py-8 px-4 border-t border-border/50">
      <div className="max-w-6xl mx-auto text-center">
        <p className="text-xs text-gray-400 leading-relaxed">
          Самозанятый Минаев Владимир Александрович, ИНН 774311723229.{" "}
          <a href="/policy.html" className="text-gray-500 hover:text-gray-700 underline underline-offset-2 transition-colors">
            Пользовательское соглашение
          </a>
          . Связаться:{" "}
          <a href="mailto:umklaidet@yandex.ru" className="text-gray-500 hover:text-gray-700 underline underline-offset-2 transition-colors">
            umklaidet@yandex.ru
          </a>
        </p>
      </div>
    </footer>
  );
};

export default Footer;