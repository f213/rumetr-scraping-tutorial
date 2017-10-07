# Как писать парсеры для руметра

## Цель

Руметр помогает пользователям выбирать квартиры в новостройках. Мы — большая таблица, как эксель — сортируем квартиры по цене,
расстоянию до метро и площади, запоминаем избранные квартиры.

Что поддерживать актуальную базу, мы пишем скрейперы, которые обходят сайты застройщиков (или отдельных новостроек).
Задача скрейпера — передавать в базу как можно больше актуальных квартир, избегая передачи неактуальных — проданых,
без цены\площади\этажа и т.д.

## Архитектура

Обычно один парсер обрабатывает одного застройщика, к примеру один парсер для ПИК, один для А101.
Есть исключения — иногда парсер может обрабатывать только одну новостройку, мы так сделали с [Зиларт](http://zilart.ru).

Мы рекомендуем писать парсеры при помощи Scrapy — это самый продвинутый фреймворк для парсинга сайтов.
Чтобы облегчить вам жизнь, мы разработали специальную прослойку между скрейпером и нашим API —
[rumetr-client](https://github.com/f213/rumetr-client).

Парсеры работают через REST API. При каждом запуске они отправляют на сервер весь набор найденных квартир.
Не нужно морочиться о формате данных или о том, как сохранять квартиры — все это уже решено в rumetr-client.

Наш клиент состоит из [айтема](https://docs.scrapy.org/en/latest/topics/items.html), который определяет формат ответа данных, и [пайплайна](https://docs.scrapy.org/en/latest/topics/item-pipeline.html),
который загружает данные на сервер. Работает это так:

```python
# settings.py

# Добавляем пайплайн, который загружает все найденные квартиры в нашу базу
ITEM_PIPELINES = {
    'rumetr.scrapy.UploadPipeline': 300,
}

# spider.py
# developer/developerspider.py

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

## Образец

В этом репозитории есть бойлерплейт — парсер для компании ПИК. За образец можно взять его. Не забудьте прописать актуальные настройки в settings.py
