# Как писать парсеры для руметра

## Цель

Руметр помогает пользователям выбирать квартиры в новостройках. Мы — большая таблица со всеми функциями экселя: сортируем квартиры по цене, расстоянию до метро и площади, запоминаем избранные квартиры.

Что поддерживать актуальную базу, мы пишем скрейперы, которые обходят сайты застройщиков. Задача скрейпера — передавать в базу как можно больше актуальных квартир, избегая передачи неактуальных — проданых, без цены\площади\этажа и т.д.

Чтобы написать скрейпер, нужно знать **Python 3** и **[Scrapy](https://scrapy.org)**.

## Архитектура

Обычно один парсер обрабатывает одного застройщика, к примеру один парсер для ПИК, один для А101.
Есть исключения — иногда парсер может обрабатывать только одну новостройку, мы так сделали с [Зиларт](http://zilart.ru).

Мы принимаем данные через REST API, и чтобы облегчить вам жизнь, мы разработали специальную прослойку между Scrapy и нашим API —
[rumetr-client](https://github.com/f213/rumetr-client).

Клиент помогает писать [идемпотентные](https://ru.wikipedia.org/wiki/Идемпотентность) парсеры, которые можно запускать хоть каждый день — в базу добавятся только новые квартиры. Не нужно морочиться о формате данных или о том, как сохранять квартиры — все это уже решено.

Наш клиент состоит из [айтема](https://docs.scrapy.org/en/latest/topics/items.html), который определяет формат ответа данных, и [пайплайна](https://docs.scrapy.org/en/latest/topics/item-pipeline.html),
который загружает данные на сервер. Работает это так:

```python
# settings.py

# Добавляем пайплайн, который загружает все найденные квартиры в нашу базу
ITEM_PIPELINES = {
    'rumetr.scrapy.UploadPipeline': 300,
}

# spider.py

from rumetr.scrapy import ApptItem as Item

def your_scrapy_callback(response):
      """Для каждоый найденной квартиры возвращаем Айтем нашего формата"""
      for appt in response.css('.your-appt[selector]):
         yield Item(
            complex_name=response.meta['complex_name'],
            complex_id=response.meta['complex_id'],
            complex_url=URL + response.meta['complex_url'] + '/',
            addr=response.meta['complex_addr'],

            house_id=appt['house_id'],
            house_name=appt['house_name'],
            house_url=URL + response.meta['complex_url'],

            id=appt['id'],
            floor=floor_number,
            room_count=appt['roomQuantity'] if appt['roomQuantity'] not in ['С', 'C'] else 1,
            is_studio=appt['roomQuantity'] in ['С', 'C'],
            square=appt['wholeAreaBti'],
            price=appt['wholePrice'],
         )
```

Небольшие пояснения к сущностям:
* `Complex` — это ЖК, несколько домов объединенных одним названием. К примеру Зиларт, или Новое Тушино
* `House` — это дом внутри ЖК. Некоторые называют их секциями.
* `Appt` — квартира. Это — единица смысла вашего парсера. Вам не нужно создавать новые ЖК или дома — достаточно отдавать квартриру, указывая к какому дому и ЖК она принадлежит — дальше rumetr-client разберется сам.

## Что делать

В этом репозитории есть бойлерплейт — парсер для компании ПИК. Его можно взять за образец.

Для того, чтобы настроить связь с нашим API нужно укзазать 3 переменные окружения:
* `RUMETR_API_HOST` — адрес нашего API. По-умолчанию это адрес нашей песочницы, можно не менять.
* `RUMETR_TOKEN` — авторизовационый токен. Можно взять в [админке песочиницы](https://sandbox.rumetr.com/admin/authtoken/token/).
* `RUMETR_DEVELOPER` — идентификатор застройщика, для которого вы пишете парсер. В песочнице у нас один застройщик, его ИД можно тоже взять в [админке](https://sandbox.rumetr.com/admin/developers/developer/).

Настройки задаются либо в переменных окружения, либо в файле .env. Формат файла .env можно посмотреть в этом же репозитории.

Когда настроите, можно приступать к разработке. В результате ваш парсер должен оказаться в файле `scraper/spiders/spider.py`. Перед сдачей обязательно полностью прогоните спайдера на нашей песочнице — так вы исключите возможность появления ошибок.
