FROM python:3.5

WORKDIR /scraper
ADD requirements.txt /scraper
RUN pip install -r requirements.txt

ADD . /scraper
CMD scrapy runspider scraper/spiders/spider.py