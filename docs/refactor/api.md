# Описание API

Этот раздел содержит полный список эндпоинтов для всех микросервисов, а также описание текущих проблем, связанных с их реализацией.

### **Эндпоинты основного сервиса (Django)**

#### **Внутренние маршруты (работают с БД и логикой внутри текущего микросервиса)**
- `GET /api/internal/csrf/` — получение CSRF-токена.
- `GET/POST/DELETE /api/internal/2gis_profiles/` — список профилей 2ГИС, создание нового профиля.
- `POST/DELETE /api/internal/2gis_profiles/<str:action>/` — действия с профилями (требуют указания действия).
- `POST/DELETE /api/internal/2gis_profiles/<str:action>/<int:profile_id>/` — действия с конкретным профилем.
- `GET /api/internal/2gis_filials/<int:profile_id>/` — получение филиалов 2ГИС.
- `GET/POST/DELETE /api/internal/flamp_profiles/` — список профилей Flamp, создание нового профиля.
- `POST/DELETE /api/internal/flamp_profiles/<str:action>/` — действия с профилями Flamp.
- `POST/DELETE /api/internal/flamp_profiles/<str:action>/<int:profile_id>/` — действия с конкретным профилем.
- `GET /api/internal/flamp_filials/<int:profile_id>/` — получение филиалов Flamp.

#### **Внешние маршруты (Django проксирует запросы к другим микросервисам)**
- `POST /api/external/api_2gis_profiles/<str:action>/` — действия с профилями 2ГИС.
- `POST /api/external/api_2gis_reviews/<str:action>/<int:review_id>/` — действия с отзывами 2ГИС.
- `POST /api/external/api_flamp_profiles/<str:action>/` — действия с профилями Flamp.
- `POST /api/external/api_flamp_reviews/<str:action>/<int:review_id>/` — действия с отзывами Flamp.

---

### **Эндпоинты микросервисов (FastAPI)**

#### **Отзывы**
- `GET /api/reviews/{filial_id}` — получение отзывов по филиалу.
- `PATCH /api/reviews/{review_id}/favorite` — отметка отзыва как избранного.

#### **Ответы на отзывы**
- `GET /api/reviews/{user_id}/answers` — получение ответов пользователя.
- `POST /api/reviews/{review_id}/answer` — отправка ответа на отзыв.
- `DELETE /api/reviews/{user_id}/answer` — удаление ответа.

#### **Жалобы**
- `POST /api/reviews/{review_id}/complaint` — подача жалобы на отзыв.

#### **Пользователи**
- `POST /api/users/create` — создание пользователя.
- `PATCH /api/users/{owner_id}/update` — обновление данных пользователя.

#### **Филиалы**
- `GET /api/filials/{filial_id}/stats` — получение статистики по филиалу.

---

### **Проблемы текущей реализации API**
1. **Несогласованные форматы ответов** — разные микросервисы возвращают данные в разных структурах.
2. **Отсутствие единых стандартов ошибок** — разные сервисы используют разные коды и форматы ошибок.
3. **Разные механизмы аутентификации** — часть сервисов работает через Django-сессию, другие через токены.

Этот раздел документации помогает понять текущее состояние API и выявить проблемы, которые необходимо исправить в процессе рефакторинга.

API будут шаблонные, изменяться будут только названия микросервисов.