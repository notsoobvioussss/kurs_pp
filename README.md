# O&G Threat Lens

Радар инцидентов и киберугроз для нефтегазовой отрасли.

## Структура проекта

- `public/` - статические файлы сайта (HTML, CSS, JS)
- `data/` - данные новостей (JSON)
- `scraper/` - скрипт для парсинга новостей

## Развертывание на GitHub Pages

### Автоматический деплой

Проект настроен для автоматического развертывания на GitHub Pages через GitHub Actions.

### Шаги для развертывания:

1. **Создайте репозиторий на GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/ВАШ_USERNAME/ВАШ_РЕПОЗИТОРИЙ.git
   git push -u origin main
   ```

2. **Включите GitHub Pages в настройках репозитория:**
   - Перейдите в Settings → Pages
   - В разделе "Source" выберите "GitHub Actions"
   - Сохраните изменения

3. **После первого push** GitHub Actions автоматически развернет сайт
   - Проверьте статус в разделе "Actions"
   - После успешного деплоя сайт будет доступен по адресу:
     `https://ВАШ_USERNAME.github.io/ВАШ_РЕПОЗИТОРИЙ/`

### Обновление данных

Для обновления данных новостей:
1. Запустите скрипт парсера: `python scraper/fetch_news.py`
2. Закоммитьте изменения: `git add data/news.json && git commit -m "Update news" && git push`

## Локальная разработка

Для локального запуска используйте любой HTTP-сервер:

```bash
# Python 3
cd public
python -m http.server 8000

# Node.js (если установлен)
npx serve public
```

Затем откройте в браузере: `http://localhost:8000`

