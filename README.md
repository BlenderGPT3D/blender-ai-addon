# AI Copilot for Blender

Add-on для Blender, который превращает вьюпорт в чат с **агентом OpenCode**. Опишите словами или покажите картинкой, что нужно создать или изменить — агент сгенерирует Python-код (`bpy`) и аддон выполнит его прямо в сцене.

Главная особенность: аддон **сам скачивает портативный OpenCode** при первом запуске — устанавливать OpenCode в систему не нужно.

## Как это работает

```
Панель в Blender (N-sidebar)
   │  кнопка "Install OpenCode"
   ▼
Скачивание портативного бинарника (~80 МБ) из GitHub Releases
и распаковка в папку аддона            ← основная установка не нужна
   │  кнопка "Start Server"
   ▼
opencode serve --port 4096 (скрытый процесс)
   │  POST /session/:id/message
   ▼
Агент читает scene_context.txt + reference_image.png,
возвращает ```python```-скрипт
   │
   ▼
Аддон исполняет его в bpy и показывает результат;
при ошибке лог автоматически уходит агенту на исправление
```

## Возможности

- **Портативный OpenCode** — скачивается и запускается из папки аддона, ничего не пишет в систему
- **Чат в 3D-вьюпорте** — история сообщений, сессии агента
- **Создание по картинке** — прикрепите файл или скриншот вьюпорта
- **Auto-run + Auto-fix** — сгенерированный код выполняется автоматически; при ошибке агент получает лог и чинит скрипт сам
- **Провайдеры** — OpenAI, OpenRouter, Anthropic, Groq, DeepSeek, локальная Ollama
- Защитный конфиг: агенту запрещён shell (`bash: deny`), правки файлов — только в рабочей папке

## Установка

1. Скачайте zip из [Releases](https://github.com/BlenderGPT3D/blender-ai-addon/releases)
2. `Edit > Preferences > Add-ons > Install` → выберите zip
3. Откройте сайдбар (`N`) → вкладка **AI Copilot**
4. Нажмите **Install OpenCode** — аддон скачает и распакует рантайм (~80 МБ, прогресс-бар)
5. В **AI Settings** выберите провайдера, вставьте API-ключ и модель
6. Нажмите **Start Server** — статус сменится на «OpenCode ready»
7. Пишите запрос и жмите **Send**

### Из исходников
```bash
git clone https://github.com/BlenderGPT3D/blender-ai-addon.git
```
Заархивируйте содержимое репозитория в zip (чтобы `blender_manifest.toml` был в корне) и установите как выше.

## Настройка модели

| Провайдер | Ключ | Пример модели |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` |
| OpenRouter | `OPENROUTER_API_KEY` | `anthropic/claude-sonnet-4` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4` |
| Groq | `GROQ_API_KEY` | `llama-3.2-90b-vision` |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| Ollama (локально) | не нужен | `llava` |

Для работы с картинками нужна vision-модель (`gpt-4o`, `claude-*`, `llava`).

## Где что лежит

Портативный рантайм и рабочие файлы хранятся в данных пользователя Blender:

```
<blend-user-dir>/datafiles/ai_copilot/
├── runtime/     # бинарник opencode
├── workspace/   # AGENTS.md, scene_context.txt, reference_image.png
├── config/      # opencode.json (правила и разрешения агента)
├── data/        # сессии OpenCode
└── server.log   # лог сервера (для отладки)
```

## Траблшутинг

- **«error: ...» при установке** — проверьте интернет и повторите; URL берётся из API GitHub Releases автоматически под вашу платформу (Windows/macOS/Linux, x64/arm64)
- **Сервер не стартует** — загляните в `server.log`; чаще всего неверный API-ключ провайдера
- **Порт занят** — смените Port в настройках (по умолчанию 4096)
- **Агент возвращает текст без кода** — просто попросите: «верни полный python-скрипт»

## Дорожная карта

- [ ] Кнопка отмены (`/session/:id/abort`)
- [ ] Экспорт результатов агента (mesh/ассеты) в .blend-папку
- [ ] Режим image-to-3D через Meshy/Tripo

## Лицензия

MIT — см. [LICENSE](LICENSE).
