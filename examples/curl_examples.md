# Ozodon: Примеры curl-запросов ко всем функциям проекта

Перед началом установите базовый URL вашего инстанса (замените на свой домен/порт):

- Для Unix/macOS: export BASE="http://localhost:8000"
- Для Windows PowerShell: $env:BASE = "http://localhost:8000"

Ниже все запросы показаны в виде curl. Если используете PowerShell, экранируйте кавычки согласно правилам PowerShell.


## 1) ActivityPub / Федеративные эндпоинты (main.py)

- Inbox (общий)
  curl -X POST "%BASE%/inbox" \
       -H "Content-Type: application/activity+json" \
       --data @examples/Offer.json

- Пользователь (Actor profile)
  curl "%BASE%/users/anna" 

- Inbox пользователя (делегирует в общий inbox)
  curl -X POST "%BASE%/users/anna/inbox" \
       -H "Content-Type: application/activity+json" \
       --data @examples/Offer.json

- Outbox пользователя
  curl "%BASE%/users/anna/outbox"

- Followers пользователя
  curl "%BASE%/users/anna/followers"

- Following пользователя
  curl "%BASE%/users/anna/following"

- WebFinger
  curl "%BASE%/.well-known/webfinger?resource=acct:anna@localhost:8000"
  Примечание: замените домен на ваш фактический HUB_DOMAIN без схемы.

- NodeInfo index
  curl "%BASE%/.well-known/nodeinfo"

- NodeInfo 2.0
  curl "%BASE%/nodeinfo/2.0"

- Публичная лента (latest offers)
  curl "%BASE%/timeline/public?limit=10"

- Простое API: товары
  curl "%BASE%/api/v1/products?q=mug&tag=market&min_price=0&max_price=100&limit=20"


## 2) Hub эндпоинты (routes/hub.py)

- Inbox хаба (индексация Offer и fedmarket:Trust)
  Отправка Offer (используем готовый пример):
  curl -X POST "%BASE%/hub/inbox" \
       -H "Content-Type: application/activity+json" \
       --data @examples/Offer.json

  Отправка Trust (пример объекта в теле):
  curl -X POST "%BASE%/hub/inbox" \
       -H "Content-Type: application/activity+json" \
       -d @- <<'JSON'
  {
    "type": "fedmarket:Trust",
    "actor": "https://shop1.example/users/bob",
    "object": {
      "target": "https://shop1.example/users/anna",
      "weight": 0.8
    },
    "published": "2025-09-01T12:00:00Z"
  }
JSON

- Поиск по товарам (JSON)
  curl "%BASE%/hub/search?q=wallet&tag=market&min_price=0&max_price=100&limit=20"

- Репутация продавца (trust score)
  curl "%BASE%/hub/trust/score?actor=https://shop1.example/users/anna"

- Список известных хабов
  curl "%BASE%/hub/hubs"

- Профиль продавца (агрегированная информация + его офферы)
  curl "%BASE%/hub/seller/https:%2F%2Fshop1.example%2Fusers%2Fanna"
  Примечание: actor_id в пути должен быть URL-encoded.

- Лента новых товаров
  curl "%BASE%/hub/feeds/latest?limit=10"

- Популярные теги
  curl "%BASE%/hub/tags?limit=50"

- Категории (упрощённо по верхним тегам)
  curl "%BASE%/hub/categories"

- Репликация между хабами (принимает такие же объекты, как /hub/inbox)
  curl -X POST "%BASE%/hub/replicate" \
       -H "Content-Type: application/activity+json" \
       --data @examples/Offer.json

- Информация о хабе
  curl "%BASE%/hub/info"


## 3) Веб-интерфейс (routes/web.py) — HTML ответы

- Главная страница поиска
  curl -i "%BASE%/"

- Альтернативный путь поиска
  curl -i "%BASE%/search?q=wallet"

- Хаб: главная UI
  curl -i "%BASE%/hub"

- Хаб: поиск UI
  curl -i "%BASE%/hub/search?q=mug&tag=market"

- Страница товара (заглушка)
  curl -i "%BASE%/hub/product/abc123"

- Страница продавца (заглушка)
  curl -i "%BASE%/hub/seller/https:%2F%2Fshop1.example%2Fusers%2Fanna"


## 4) Дополнительно

- Подача Offer через общий /inbox также инициирует репликацию на пиров (если HUB_MODE включён), как и fedmarket:Trust:
  curl -X POST "%BASE%/inbox" \
       -H "Content-Type: application/activity+json" \
       --data @examples/Offer.json

Подсказки:
- Для POST JSON всегда используйте заголовок Content-Type: application/activity+json.
- В Windows PowerShell для here-doc используйте другой способ передачи данных (например, сохраните JSON во временный файл и передайте через --data @file.json), либо примените @"..."@ строковые литералы.
