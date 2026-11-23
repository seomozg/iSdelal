# 🤖 Документ-бот — лендинг

Одностраничный лендинг для пользователей рабочего Telegram-бота: что это за бот,
зачем он нужен и как им пользоваться — понятно за несколько секунд.

Бот **уже работает** (<https://t.me/iManagerOfficialBot>): пользователям ничего
устанавливать и настраивать не нужно — только открыть ссылку. Никаких
BotFather, серверов и деплоя в лендинге не упоминается.

**Статика без сборки и без JS**: один `index.html` + `styles.css`.
FAQ — на нативном `<details>`, адаптив — чистый CSS.

## Структура

```
docbot-landing/
  index.html    hero с мокапом чата + полоса «Кому пригодится»,
                «Как пользоваться» (3 шага), возможности,
                таблица команд, FAQ, CTA
  styles.css    все стили (шапка/футер, адаптив ≤900/720px)
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
| Ссылка на бота | `https://t.me/iManagerOfficialBot` — 4 места в `index.html` (шапка, hero, CTA, футер) |
| Тексты ответов в мокапе чата | блок `.chat-card` в `index.html` |
| Полоса «Кому пригодится» | блок `.strip` в `index.html` |
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
