# Какие функции должен поддерживать хаб Ozodon

## 🌐 **1. Как федеративное приложение (в стиле Mastodon / Fediverse)**  
Хаб — это **инстанс Fediverse**, совместимый с **ActivityPub**, и должен следовать стандартам:
- [ActivityPub W3C](https://www.w3.org/TR/activitypub/)
- [Fediverse Protocol Best Practices](https://docs.joinmastodon.org/spec/activitypub/)
- [Security & Discovery (WebFinger, NodeInfo)](https://nodeinfo.diaspora.software/)

### ✅ Основные функции (федеративные)

| Функция | Назначение | URL |
|--------|-----------|-----|
| **ActivityPub Inbox/Outbox** | Приём и отправка федеративных действий | `/.well-known/webfinger`, `/users/{username}/inbox`, `/users/{username}/outbox` |
| **WebFinger** | Поиск пользователей (`acct:anna@ozodon.net`) | `/.well-known/webfinger?resource=acct:user@domain` |
| **NodeInfo** | Метаданные об инстансе (версия, ёмкость, софт) | `/.well-known/nodeinfo`, `/nodeinfo/2.0` |
| **Федеративная подписка (Follow)** | Подписка на магазины/продавцов | `/users/{id}/follow` (ActivityPub `Follow`) |
| **Рассылка обновлений** | Отправка `Create`, `Offer`, `Update` подписчикам | Через `outbox` → доставка в `inbox` других инстансов |
| **Публичная лента (только для хаба)** | Показ новых товаров из сети | `/timeline/public` |
| **Поиск пользователей и аккаунтов** | Поиск продавцов по `@username@domain` | `/search?q=@anna&type=accounts` |
| **Поддержка кэша объектов (акторов)** | Хранение профилей удалённых продавцов | `/users/{remote_id}` (виртуальный актор) |
| **Подпись ActivityPub-объектов (HTTP Signatures)** | Аутентификация действий | Заголовки `Signature`, `Date` |
| **Доставка (Delivery)** | Отправка событий другим инстансам | `POST /inbox` на удалённые серверы |

---

## 🛍️ **2. Как маркетплейс (Ozodon-специфичные функции)**  
Хаб должен индексировать и упрощать доступ к **товарам, сделкам, репутации**, используя федеративные данные.

### ✅ Основные функции (маркетплейс)

| Функция | Назначение | URL |
|--------|-----------|-----|
| **Приём и индексация `Offer`** | Сбор объявлений от всех инстансов | `POST /hub/inbox` |
| **Глобальный поиск по товарам** | По названию, тегу, цене, репутации | `GET /hub/search?q=...&tag=...` |
| **Индивидуальный рейтинг (репутация)** | На основе Web of Trust | `GET /hub/trust/score?actor={id}` |
| **Реестр хабов** | Обнаружение других индексов | `GET /hub/hubs` |
| **Репликация между хабами** | Синхронизация данных для отказоустойчивости | `POST /hub/replicate` (автоматически) |
| **Просмотр профиля продавца** | Информация, отзывы, репутация | `/hub/seller/{actor_id}` |
| **Категории и теги** | Навигация по типам товаров | `/hub/tags`, `/hub/categories` |
| **Список новых товаров** | Лента "новинок" | `/hub/feeds/latest` |
| **Ранжирование результатов** | По цене, репутации, расстоянию (если гео) | В `/hub/search` — веса: `score = price * (1.5 - trust)` |
| **API для клиентов** | Доступ к данным без ActivityPub | `GET /api/v1/products`, `GET /api/v1/reviews` |
| **Веб-интерфейс (frontend)** | Поиск, просмотр, переход к оплате | `/hub`, `/hub/product/{id}` |
| **Оплата с эскроу (TON)** | Бронь товара и блокировка средств, подтверждение/возврат | `POST /hub/payments/escrow`, `POST /hub/payments/{deal_id}/confirm`, `POST /hub/payments/{deal_id}/refund`, `GET /hub/payments/{deal_id}` |

---

## 🔐 Дополнительно: безопасность и модерация

| Функция | URL |
|--------|-----|
| **Спам-фильтрация через WoT** | При `Flag` — проверка доверия репортёра |
| **Чёрные списки (блокировки)** | `/hub/moderation/blocked-instances` |
| **Жалобы (Flag)** | `POST /inbox` с `type: Flag` |
| **Отзывы (Review)** | Через `Like` или `Announce` с объектом `Review` |

---

## 📌 Рекомендуемая структура URL (роутинг)

### 🌐 Федеративные эндпоинты (общие для Fediverse)
```
/.well-known/webfinger
/.well-known/nodeinfo
/nodeinfo/2.0
/users/{username}/inbox
/users/{username}/outbox
/users/{username}          → профиль актора
/followers, /following
```

### 🛒 Маркетплейс-функции (Ozodon Hub)
```
/hub/inbox                 → приём Offer, Trust
/hub/search                → поиск товаров
/hub/trust/score?actor=... → репутация
/hub/hubs                  → список хабов
/hub/seller/{id}           → профиль продавца
/hub/feeds/latest          → новые товары
/hub/tags                  → популярные теги
/hub/info                  → статистика хаба

# Платежи и эскроу (TON)
/hub/payments/escrow       → создать сделку: бронь + заморозка средств
/hub/payments/{deal_id}    → получить состояние сделки
/hub/payments/{deal_id}/confirm → подтвердить доставку (release)
/hub/payments/{deal_id}/refund  → запросить возврат
```

### 🖥️ Веб-интерфейс
```
/hub                       → главная страница поиска
/hub/product/{id}         → карточка товара
/hub/seller/{id}          → страница продавца
```

### 📡 API (опционально)
```
/api/v1/products?q=...
/api/v1/sellers/{id}/reviews
```

---

## ✅ Итог: хаб Ozodon — это **гибрид**

| Роль | Что делает |
|------|------------|
| **Федеративный узел** | Полноценный участник Fediverse: принимает/отправляет ActivityPub, поддерживает WebFinger, NodeInfo |
| **Маркет-хаб** | Индексирует товары, ранжирует по репутации, предоставляет API и веб-интерфейс |
| **Роутер доверия** | Распространяет и вычисляет Web of Trust |
| **Реплицируемый индекс** | Синхронизируется с другими хабами для отказоустойчивости |

---

## 💡 Лучшие практики

1. **Не дублируй данные без необходимости** — храните ссылки на оригинальные `id`.
2. **Подписывай все исходящие объекты** — HTTP Signatures.
3. **Кэшируй акторов и объекты** — но обновляй при `Update`.
4. **Разрешай деиндексацию** — если `Delete` приходит, удаляй из хаба.
5. **Используй `#market` как основной тег** для обнаружения.
6. **Позволяй экспортировать данные** — например, `GET /hub/offers.json`.
