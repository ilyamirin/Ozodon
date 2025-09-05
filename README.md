# Ozodon — децентрализованный маркетплейс на основе Mastodon/ActivityPub

Ozodon — это минималистичный узел (node) для «федеративного» маркетплейса. Он использует протокол ActivityPub (тот же, что и в экосистеме Mastodon) для распространения объявлений о товарах (Offer), обмена сигналами доверия между участниками (Trust) и базовые механизмы модерации на основе доверия. Платёжная логика демонстрируется на примере TON (эскроу, имитация).

Проект задуман как демонстрационный/референс‑узел: упростить запуск, показать ключевые концепции и оставить пространство для вашей дальнейшей разработки.

## Возможности
- Приём и сохранение предложений (Offer) с описанием товара по ActivityPub
- Публикация и учёт связей доверия (fedmarket:Trust) между акторами
- Простейшая модерация репортов (Flag) с проверкой репортёра по доверительной сети
- Эндпоинт для создания имитации TON‑эскроу сделки
- REST API на FastAPI, хранение в MongoDB (Motor)

## Архитектура (высокоуровнево)
- ActivityPub-сообщения описываются в activitypub.py (Offer, Trust) и принимаются узлом в /inbox
- Данные (товары/офферы/доверие/репорты) сохраняются в MongoDB (database.py)
- Сервис доверия (services/trust_service.py) строит простые графы и передаёт вес доверия по цепочкам
- TON-платежи (services/ton_payment.py) реализованы как безопасные заглушки с опциональными зависимостями
- Основные HTTP‑эндпоинты определены в main.py

## Требования
- Python 3.10+
- MongoDB (локально или в облаке)

Рекомендуемые пакеты Python (минимум):
- fastapi
- uvicorn[standard]
- motor
- pydantic

Опционально (для реальной интеграции TON — в проекте предусмотрены безопасные заглушки):
- tonutils (или аналогичный SDK)

## Установка и запуск
1) Клонируйте репозиторий и установите зависимости:

   pip install fastapi uvicorn[standard] motor pydantic

   (Необязательно) Для TON:

   pip install tonutils

2) Установите переменные окружения (см. раздел «Конфигурация»).

3) Запустите MongoDB (локально):
- По умолчанию узел ожидает MongoDB на mongodb://localhost:27017, БД ozodon

4) Запустите приложение:

   uvicorn main:app --reload --host 0.0.0.0 --port 8000

После запуска API будет доступно по адресу: http://localhost:8000
Документация Swagger UI: http://localhost:8000/docs

## Конфигурация
Все параметры собираются из переменных окружения в config.py:
- MONGODB_URI — строка подключения к MongoDB (по умолчанию mongodb://localhost:27017)
- DATABASE_NAME — имя БД (по умолчанию ozodon)
- TON_API_KEY — API‑ключ для Tonapi (опционально)
- TON_WALLET_MNEMONIC — мнемоника кошелька TON (строка из слов, разделённых пробелами), опционально
- HUB_URL — URL «хаба»/агрегатора федерации (демо‑значение)

Пример для Windows PowerShell:

$env:MONGODB_URI = "mongodb://localhost:27017"
$env:TON_API_KEY = ""
$env:TON_WALLET_MNEMONIC = "word1 word2 ... word24"
$env:HUB_URL = "https://hub.fedmarket.example"

## Эндпоинты
- POST /inbox — входящая точка ActivityPub
  Поддерживаемые типы:
  - Offer — товарное предложение. Пример: examples/Offer.json
  - fedmarket:Trust — связь доверия между двумя акторами
  - Flag — репорт (учитывается только при достаточном доверии к репортёру)

  Пример запроса (Offer):

  curl -X POST http://localhost:8000/inbox \
       -H "Content-Type: application/json" \
       -d @examples/Offer.json

- GET /products — получить список товаров, сохранённых узлом

  Пример:

  curl http://localhost:8000/products

- POST /trust — создать/задекларировать связь доверия в локальной БД и получить ActivityPub‑объект Trust
  Тело запроса (JSON):
  {
    "source": "https://shop1.example/users/alice",
    "target": "https://shop2.example/users/bob",
    "weight": 0.8,
    "proof_signature": "<ваша‑подпись>"
  }

  Пример:

  curl -X POST http://localhost:8000/trust \
       -H "Content-Type: application/json" \
       -d '{
            "source": "https://shop1.example/users/alice",
            "target": "https://shop2.example/users/bob",
            "weight": 0.8,
            "proof_signature": "sig"
          }'

- POST /pay/escrow — создать имитацию TON‑эскроу сделки
  Параметры запроса (query/form): buyer_addr: str, amount: float

  Пример:

  curl -X POST "http://localhost:8000/pay/escrow?buyer_addr=UQ_ABC&amount=0.5"

Ответ:
{
  "deal_id": "deal_...",
  "buyer": "UQ_ABC",
  "seller": "UQ_FAKE_ADDRESS",
  "amount_ton": 0.5,
  "amount_nano": 500000000,
  "status": "frozen",
  "timeout_days": 7,
  "contract_address": "UQ_FAKE_ADDRESS"
}

## Форматы сообщений ActivityPub
См. activitypub.py. Ключевые элементы:
- Offer: object.type = schema:Product, поля schema:name, schema:description, schema:image, schema:offers (schema:price, schema:priceCurrency)
- Trust: type = fedmarket:Trust, object.type = fedmarket:TrustRelationship, object.target, object.weight
- Теги: массив tag с объектами {"type": "Hashtag", "name": "#market"} и т. п.

Пример Offer — examples/Offer.json.

## Доверие и модерация
- Связи доверия сохраняются в коллекцию trust_log
- Итоговый балл доверия между A и B считается рекурсивно (compute_trust_score) с ограниченной глубиной и затуханием весов
- Порог для принятия репортов (Flag) — 0.3

## Хранение данных
Коллекции MongoDB (имена создаются по обращению):
- products — нормализованное представление товаров для вывода списка
- offers — оригинальные входящие ActivityPub‑Offer
- trust_log — связи доверия
- flags — принятые репорты

## Заметки по безопасности и продакшену
- Подписывание/валидация ActivityPub (HTTP Signatures, подпись объектов) опущены — добавляйте перед выводом в федерацию
- В services/ton_payment.py предусмотрены «мягкие» заглушки на случай отсутствия SDK или ключей: приложение не падает
- Настройте CORS/аутентификацию под ваши сценарии
- Храните секреты вне репозитория, используйте .env/секрет‑хранилища

## Дорожная карта
- Поддержка outbox/подписки узлов и реальной федерации
- Подписи ActivityPub и валидация входящих сообщений
- Настоящий смарт‑контракт TON (эскроу) и подтверждения доставки/возврата
- Поисковый индекс и фильтры по товарам/тегам
- Панель модератора с учётом доверительных цепочек

## Лицензия
MIT