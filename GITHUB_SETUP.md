# GitHub Setup для iSdelal

## Шаг 1: Инициализация репозитория

### На локальной машине:

```powershell
cd c:\Users\HONOR\Desktop\dev\iSdelal

# Инициализировать Git
git init

# Проверить статус
git status

# Добавить все файлы (кроме .gitignore)
git add .

# Проверьте что .env НЕ добавлен (он в .gitignore)
git status
# backend\.env должен быть пропущен!

# Первый коммит
git commit -m "Initial commit: RAG kit with Qdrant + FastAPI + Nginx"
```

## Шаг 2: Создать репозиторий на GitHub

### На GitHub.com:

1. Откройте https://github.com/new
2. Заполните:
   - **Repository name:** `iSdelal`
   - **Description:** `RAG Kit: Qdrant Vector DB + FastAPI (OpenAI) + Nginx + JS Widget`
   - **Public / Private:** Выберите нужное
   - **НЕ инициализируйте с README** (у вас уже есть локально)
3. Нажмите "Create repository"

### На локальной машине:

```powershell
cd c:\Users\HONOR\Desktop\dev\iSdelal

# Добавить remote origin (замените на ваш URL)
git remote add origin https://github.com/yourusername/iSdelal.git

# Проверить remote
git remote -v
# origin  https://github.com/yourusername/iSdelal.git (fetch)
# origin  https://github.com/yourusername/iSdelal.git (push)

# Пушить на GitHub
git branch -M main
git push -u origin main

# Готово! Репозиторий теперь на GitHub
```

## Шаг 3: Настроить Secrets для GitHub Actions

GitHub Actions нужны ваши ключи для запуска тестов. Сделайте их приватными через **Secrets**.

### Добавить OPENAI_API_KEY:

1. На GitHub: перейдите в **Settings → Secrets and variables → Actions**
2. Нажмите "New repository secret"
3. **Name:** `OPENAI_API_KEY`
4. **Value:** `sk-...` (ваш ключ из `backend/.env`)
5. Нажмите "Add secret"

### (Опционально) Добавить DEPLOY_KEY:

Если хотите автоматический деплой на test-domain.ru:

1. Создайте SSH ключ на сервере:
```bash
# На test-domain.ru сервере:
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github-deploy
cat ~/.ssh/github-deploy.pub >> ~/.ssh/authorized_keys
```

2. На GitHub добавьте приватный ключ:
   - **Settings → Secrets and variables → Actions**
   - **New secret:** `DEPLOY_KEY`
   - **Value:** Содержимое `~/.ssh/github-deploy` (приватный ключ!)

3. Поправьте `.github/workflows/deploy.yml` с вашими данными сервера

## Шаг 4: Проверить GitHub Actions

### Первый запуск тестов:

1. На GitHub нажмите **Actions**
2. Выберите **Tests** workflow
3. Нажмите "Run workflow" → "Run workflow"
4. Смотрите логи - тесты должны запуститься!

Если тесты падают:
- Нажмите на failed job → "Run workflow"
- Проверьте логи
- Убедитесь что `OPENAI_API_KEY` верный
- Или отредактируйте `.github/workflows/tests.yml`

## Шаг 5: Разработка с GitHub Flow

### Для новой фичи:

```powershell
# 1. Создать ветку
git checkout -b feature/my-feature

# 2. Разработать локально
# ... редактируйте файлы ...

# 3. Протестировать
docker compose up --build
docker compose exec backend pytest tests/ -v

# 4. Коммитить
git add .
git commit -m "Add: my-feature description"

# 5. Пушить на GitHub
git push origin feature/my-feature
```

### На GitHub:

1. Автоматически откроется suggestion "Compare & pull request"
2. Нажмите "Create pull request"
3. Заполните описание PR
4. GitHub Actions автоматически запустит тесты
5. После прохождения тестов → **Squash and merge** или **Create a merge commit**

### На main:

```powershell
# Локально обновить main
git checkout main
git pull origin main

# Или можно удалить фичу ветку
git branch -d feature/my-feature
```

## Шаг 6: Деплой с GitHub на test-domain.ru

### Вариант А: Ручной деплой (рекомендуется для начала)

```bash
# На test-domain.ru сервере:
cd /opt/iSdelal
git pull origin main
docker compose up --build -d
```

### Вариант Б: Автоматический деплой (опционально)

Если хотите автоматический деплой при merge в main:

1. Убедитесь что добавили `DEPLOY_KEY` secret (см. Шаг 3)
2. В `.github/workflows/deploy.yml` замените:
   - `host: test-domain.ru` → ваш реальный хост
   - `username: deploy_user` → ваш юзер на сервере
3. Пушьте в main → GitHub Actions автоматически деплоит на сервер!

## Бэкапы и security

### Не коммитьте секреты!

Проверяйте перед каждым коммитом:
```powershell
git status
# backend\.env НЕ должен быть в списке!
```

### Если случайно закоммитили секрет:

```powershell
# Удалить из истории (опасно! лучше используйте новый ключ)
git-filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch backend/.env' \
  --prune-empty --tag-name-filter cat -- --all

# Лучше просто измените API ключ на new ключ в OpenAI dashboard
```

## Структура веток (рекомендуется)

```
main
  ├─ production = стабильный код (deploy на test-domain.ru)
develop
  ├─ staging = перед production
feature/
  ├─ feature/add-openai-integration
  ├─ feature/improve-crawling
  └─ fix/bug-in-rag
```

Если хотите, используйте эту структуру:
```powershell
# Создать develop
git checkout -b develop
git push -u origin develop

# Используйте develop как базовую для PR вместо main
```

## Полезные GitHub фичи

### Branch Protection для main

На GitHub: **Settings → Branches**
- **Add rule** для `main`
- ✅ Require pull request reviews
- ✅ Require status checks to pass (GitHub Actions)
- ✅ Require branches to be up to date

Это гарантирует что только reviewed код попадает в main!

### Автоматические ребейсы

На GitHub: **Settings → Pull Requests**
- ✅ Allow auto-merge
- Выберите "Squash and merge"

Тогда PR автоматически мержится если тесты прошли.

## Мониторинг и logs

### GitHub Actions logs

https://github.com/yourusername/iSdelal/actions

### Когда PR падает (тесты не прошли):

1. Откройте failed workflow
2. Нажмите на failed step
3. Смотрите логи
4. Исправьте локально:
```powershell
git add .
git commit -m "Fix: test failure"
git push origin feature/my-feature
```
GitHub Actions автоматически перезапустит тесты!

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| `remote: fatal: repository not found` | Проверьте URL: `git remote -v`, может быть private repo |
| Тесты падают в Actions | Убедитесь что `OPENAI_API_KEY` secret добавлен |
| `Permission denied (publickey)` при деплое | Проверьте `DEPLOY_KEY` secret и authorized_keys на сервере |
| Хотите удалить secret | **Settings → Secrets → Delete** (нельзя просмотреть!) |

## Быстрый чеклист

- [ ] `git init` и `git remote add origin`
- [ ] Репозиторий создан на GitHub
- [ ] Первый `git push` выполнен
- [ ] `OPENAI_API_KEY` добавлен в Secrets
- [ ] GitHub Actions тесты запущены и прошли ✅
- [ ] Создана ветка `feature/first-feature`
- [ ] Pull Request создан и merged
- [ ] Деплой на test-domain.ru работает

---

**Готово!** Теперь у вас есть complete workflow: разработка локально → GitHub → деплой на продакшен сервер. 🚀
