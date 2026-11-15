# Контракт Tool

## Общий интерфейс

```text
interface Tool:
    name: string
    input_schema: JSON Schema
    execute(input: object, context: ToolContext) -> ToolResult
```

`ToolContext` содержит `job_id`, `file_storage`, `logger` и `deadline`.
`ToolResult` содержит `output_file_id` (если создан файл) и `data` (структурированные метаданные).

### Правила контракта

- Tool получает только параметры своей операции и контекст выполнения; он не получает HTTP-запрос.
- Tool возвращает `ToolResult` либо одну из типизированных ошибок.
- Tool проверяет бизнес-ограничения своих параметров; HTTP-слой проверяет JSON-структуру, типы и обязательные поля до создания Job.
- Dispatcher отвечает за выбор Tool, порядок выполнения, перевод Job в `failed` и сохранение результата.
- Tool не меняет состояние Job напрямую.
- Все Tools должны соблюдать deadline и не оставлять частично записанный файл: запись результата выполняется атомарно.

### Единый набор ошибок Tool

| Ошибка | Значение | Поведение Dispatcher |
|---|---|---|
| `INVALID_INPUT` | Параметры операции недопустимы | Job → `failed`, ошибка сохраняется |
| `UNSUPPORTED_FORMAT` | Формат не поддерживается | Job → `failed` |
| `FILE_NOT_FOUND` | Входной файл отсутствует | Job → `failed` |
| `TOOL_TIMEOUT` | Превышен deadline | Job → `failed` |
| `TOOL_INTERNAL_ERROR` | Необработанная внутренняя ошибка Tool | Job → `failed`, детали не раскрываются клиенту |

## Tool 1: ExtractTextTool

- `name`: `extract_text`
- Вход: `{ "fileId": "string", "language": "string (optional)" }`.
- Проверки: файл существует; формат входит в список поддерживаемых форматов; размер не превышает лимит.
- Выход: `{ "output_file_id": "string", "data": { "characters": "integer", "detected_language": "string|null" } }`.
- Ошибки: `FILE_NOT_FOUND`, `UNSUPPORTED_FORMAT`, `INVALID_INPUT`, `TOOL_TIMEOUT`, `TOOL_INTERNAL_ERROR`.
- Скрывает библиотеку извлечения текста и особенности DOCX/PDF/TXT.

## Tool 2: CalculateStatisticsTool

- `name`: `calculate_statistics`
- Вход: `{ "textFileId": "string" }`.
- Проверки: файл существует и содержит текст UTF-8.
- Выход: `{ "data": { "characters": "integer", "words": "integer", "sentences": "integer", "paragraphs": "integer" } }`.
- Ошибки: `FILE_NOT_FOUND`, `INVALID_INPUT`, `TOOL_TIMEOUT`, `TOOL_INTERNAL_ERROR`.
- Скрывает алгоритм токенизации и подсчёта статистики.

## Tool 3: ConvertFormatTool

- `name`: `convert_format`
- Вход: `{ "fileId": "string", "targetFormat": "txt|pdf|docx|html" }`.
- Проверки: исходный файл существует; `targetFormat` поддерживается; преобразование разрешено для исходного формата.
- Выход: `{ "output_file_id": "string", "data": { "format": "string" } }`.
- Ошибки: `FILE_NOT_FOUND`, `UNSUPPORTED_FORMAT`, `INVALID_INPUT`, `TOOL_TIMEOUT`, `TOOL_INTERNAL_ERROR`.
- Скрывает библиотеку конвертации и детали кодировок.

## Внешние зависимости

Порт для OCR, перевода и LLM не реализуется в этой версии. Если интеграция появится, она будет оформлена отдельными Tools и адаптером; Dispatcher не должен зависеть от SDK конкретного провайдера.
