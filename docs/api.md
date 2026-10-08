# API

Полная интерактивная спецификация OpenAPI 3.1 (Swagger UI): **http://localhost:8000/api/docs**
(ReDoc: `/api/redoc`, JSON: `/api/openapi.json`). Все запросы, ответы и коды ошибок описаны в
спецификации; TypeScript-типы фронтенда генерируются из неё (`npm run gen:api`). Корень backend
(`http://localhost:8000/`, а также `/docs`, `/redoc`, `/openapi.json`) перенаправляет на документацию,
`GET /api` возвращает ссылки на неё и на `/api/health`.

* Аутентификация: `Authorization: Bearer <JWT>` — токен из `/auth/login` или `/auth/verify-email`.
* Формат ошибок: `{"code": "cooldown", "message": "…", "details": {...}}` — в том числе для
  несуществующего адреса (`route_not_found`, 404) и неподдерживаемого метода (`method_not_allowed`, 405).
* Язык: заголовок `Accept-Language` (`ru` — по умолчанию, `en`). На нём возвращаются сообщения об
  ошибках (включая 422 с названием поля), объяснения подбора, рекомендации по тесту, справочники и
  тексты заданий; ответ содержит `Content-Language` и `Vary: Accept-Language`. `code` ошибки от языка
  не зависит.
* Коды: `401` нет/просрочен токен, `403` чужая роль, `404` не найдено или нет доступа, `409` конфликт
  состояния (кулдаун, дубликат, закрытое приглашение), `422` валидация, `429` лимит приглашений.

## Эндпоинты

### Аутентификация
| Метод | Путь | Назначение |
|---|---|---|
| POST | `/api/auth/register` | Регистрация (роль, согласие 152-ФЗ) → код на e-mail |
| POST | `/api/auth/verify-email` | Подтверждение кода → JWT |
| POST | `/api/auth/resend-code` | Повторная отправка кода |
| POST | `/api/auth/login` | Вход → JWT |
| GET | `/api/auth/me` | Текущий пользователь (включая `locale` — язык интерфейса) |
| PUT | `/api/auth/me/locale` | Сохранить язык интерфейса в учётной записи (`ru` / `en`) |

### Справочники
| GET | `/api/reference` | Специализации и компетенции, грейды с порогами, навыки, профили весов |
|---|---|---|

### Кабинет кандидата
| Метод | Путь | Назначение |
|---|---|---|
| GET | `/api/candidate/dashboard` | Категория, заполненность, шаги, приглашения, последний тест, предложенное задание |
| GET/PUT | `/api/candidate/profile` | Профиль, резюме, опрос (специализация, грейд), навыки, `experience` — места работы (список заменяется целиком); `categories` — все подтверждённые категории, `grade_status` — статус заявленного грейда |
| PUT | `/api/candidate/categories/{specialization_id}/primary` | Сделать категорию основной |
| POST | `/api/candidate/resume/parse` | Распознавание PDF-резюме (без сохранения): контакты, стек, грейд, стаж, места работы |
| GET/PUT | `/api/candidate/settings` | Приватность и согласие на публикацию |
| GET | `/api/candidate/fsp` | Достижения ФСП и сила сигнала |
| POST | `/api/candidate/fsp/link` · `/fsp/confirm` · `/fsp/sync` | Привязка / подтверждение / синхронизация ФСП ID |
| DELETE | `/api/candidate/fsp/link` | Отвязка |
| GET | `/api/candidate/invitations` | Входящие приглашения |
| GET | `/api/candidate/invitations/{id}` | Открыть (статус → `viewed`) |
| POST | `/api/candidate/invitations/{id}/accept` · `/reject` · `/report` | Ответ / жалоба |
| GET | `/api/candidate/tasks` | Регулярные задания: адресные предложения (с причинами и сроком), челленджи категории, мои результаты; при необходимости предлагает следующее |
| POST | `/api/candidate/tasks/{id}/submit` | Ответ: автопроверка (`correct`) или подход на проверку работодателю |
| POST | `/api/candidate/tasks/offers/{assignment_id}/decline` | Отказаться от предложенного задания |

### Тестирование
| Метод | Путь | Назначение |
|---|---|---|
| GET | `/api/candidate/testing?specialization_id=` | Доступность по грейдам (кулдауны категории этой специализации), категории, активная попытка, история, правила |
| POST | `/api/candidate/testing/start` | Сгенерировать индивидуальный вариант `{specialization_id, target_grade}` |
| GET | `/api/candidate/testing/attempts/{id}` | Вопросы попытки (без правильных ответов) |
| POST | `/api/candidate/testing/answer` | Сохранить ответ `{attempt_id, item_id, answer: [...], time_ms?, pasted?, client?: {focus_lost, away_ms, copies}}` |
| POST | `/api/candidate/testing/finish` | Завершить `{attempt_id, client?}` → грейд, категория, компетенции, уверенность, `integrity` (проверка честности) |
| GET | `/api/candidate/testing/results/{attempt_id}` | Результат |

### Кабинет работодателя
| Метод | Путь | Назначение |
|---|---|---|
| GET | `/api/employer/dashboard` | Потребности, воронка приглашений, последние ответы |
| GET/PUT | `/api/employer/profile` | Профиль компании |
| GET/POST | `/api/employer/requirements` | Потребности; создание сразу формирует подборку |
| POST | `/api/employer/requirements/parse` | Текст потребности → специализация, грейд, стек, вилка |
| GET/PUT/DELETE | `/api/employer/requirements/{id}` | Потребность: просмотр / уточнение (пересчёт) / закрытие |
| GET | `/api/employer/requirements/{id}/matches` | Подборка: `grades, categories, skills, has_fsp, min_score, shortlisted, refresh` |
| POST | `/api/employer/requirements/{id}/shortlist/{candidate_id}?value=` | Избранное |
| GET | `/api/employer/requirements/{id}/compare?a=&b=` | Почему A выше B |
| GET | `/api/employer/candidates` | Банк кандидатов с фильтрами |
| GET | `/api/employer/candidates/{id}?requirement_id=` | Профиль + объяснение; контакты — по правилам видимости |
| GET/POST | `/api/employer/invitations` | История / отправка приглашения (зарплата обязательна) |
| POST | `/api/employer/invitations/{id}/withdraw` | Отозвать |
| GET | `/api/employer/applications` · POST `/applications/{id}/status` | Отклики на вакансии |
| GET/POST | `/api/employer/tasks` | Задания компании со статистикой / публикация: `mode` (solve / approach), `audience` (targeted / category), `grade_id`, `job_id`, `competency_id`, `answer_spec`, `key_points`, `time_limit_days`, `max_offers` |
| PUT | `/api/employer/tasks/{id}/active` | Снять с публикации / вернуть |
| POST | `/api/employer/tasks/{id}/offer` | Предложить задание кандидату лично `{candidate_id}` |
| GET | `/api/employer/tasks/{id}/submissions` | Решения: автопроверка или предварительная оценка по ключевым идеям (что найдено / упущено) |
| POST | `/api/employer/submissions/{id}/review` | Оценка по рубрике `{rubric: {correctness, completeness, reasoning: 0..2}, comment}` |

### Вакансии и отклики
| GET | `/api/jobs` | Опубликованные вакансии (для кандидата — с % совпадения, обратный матчинг) |
|---|---|---|
| GET | `/api/jobs/{id}` | Вакансия |
| POST | `/api/applications` | Отклик кандидата (раскрывает контакты этому работодателю) |
| GET | `/api/applications` | Мои отклики |

### Мок реестра ФСП
| GET | `/api/mock-fsp/v1/participants/{fsp_id}` | Участник |
|---|---|---|
| GET | `/api/mock-fsp/v1/participants?email=` | Поиск по e-mail |
| GET | `/api/mock-fsp/v1/stats` | Размер мок-реестра |

## Пример: потребность → подборка → приглашение

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"hr@demo.ru","password":"demo12345"}' | jq -r .access_token)

curl -s -X POST localhost:8000/api/employer/requirements -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"title":"Backend Developer","specialization_id":"backend",
  "grade_id":"middle","must_skills":["python","fastapi","postgresql","docker"],
  "salary_from":180000,"salary_to":250000}' | jq .id

curl -s "localhost:8000/api/employer/requirements/13/matches?limit=3" -H "Authorization: Bearer $TOKEN" \
  | jq '.items[] | {name: .display_name, category: .category.label, percent: .match.percent,
        why: [.match.reasons[].text]}'
```

Фрагмент ответа:

```json
{
  "name": "Алексей Демидов", "category": "Backend · Middle", "percent": 93,
  "why": ["Специализация Backend совпадает", "Подтверждённый грейд Middle — как требуется",
          "Совместимость стека 90%: 4 из 4 обязательных навыков, 3 подтверждены тестом",
          "Тест: 76/100 (уверенность 100%)",
          "3 подтверждённых достижения ФСП: 2 место — Всероссийские соревнования по продуктовому программированию (2026)"]
}
```
