# 🤖 Документ-бот — лендинг

Простой информативный лендинг для потенциальных клиентов: как работает
Telegram-бот по документам (загрузка → индексация → ответы по вашим файлам).

**Статика без сборки и без JS**: один `index.html` + `styles.css`.
FAQ — на нативном `<details>`, адаптив — чистый CSS.

## Структура

```
docbot-landing/
  index.html    вся страница: hero с мокапом чата, «Как это работает»,
                возможности, таблица команд, для кого, FAQ, CTA
  styles.css    все стили (тёмная шапка/футер, адаптив ≤900/720px)
  README.md     этот файл
```

## Локальный просмотр

Прямо двойным кликом по `index.html` либо:

```bash
cd docbot-landing
python -m http.server 8080
# http://localhost:8080
```

## Что поменять под себя

| Что | Где |
|-----|-----|
| Ссылка на демо-бота | `https://t.me/iManagerOfficialBot` — 4 места в `index.html` (шапка, hero, CTA, футер) |
| Ссылка на основной продукт | `https://site-agent.online` — 2 места в `index.html` (CTA, футер) |
| Тексты ответов в мокапе чата | блок `.chat-card` в `index.html` |
| Цвета/акценты | CSS-переменные в начале `styles.css` (`--accent`, `--violet`) |

## Деплой

Любой статический хостинг; на текущем сервере — скопировать папку и отдать
nginx:

```nginx
server {
    listen 80;
    server_name docs-bot.example.com;
    root /var/www/docbot-landing;
    index index.html;
}
```

```bash
scp -r docbot-landing/ root@<server>:/var/www/
# на сервере: nginx -t && systemctl reload nginx
```
