import hashlib
import re

import simplejson as json

import scrapy
from rumetr.scrapy import ApptItem as Item
from scrapy.http import Request

URL = 'https://www.pik.ru'


class Spider(scrapy.Spider):
    CHESS_PLAN_URL = '{URL}{complex_url}/singlepage?data=ChessPlan&id={subcomplex_id}&private_key=1&format=json&domain=www.pik.ru'

    name = 'spider'
    allowed_domains = ['pik.ru']

    def start_requests(self):
        return [Request(URL, callback=self.home_page)]

    def home_page(self, response):
        """
        Parse the home page and make requests
        to the house list page for each found complex
        """
        complexes = self._parse_home_page(response)

        for complex in complexes:
            url = complex['url']
            url = url.split('/')[1]

            url = URL + '/' + url

            request = Request(url + '/datapages?data=GenPlan', callback=self.genplan_page)
            request.meta.update({
                'complex_id': complex['guid'],
                'complex_name': complex['name'],
                'complex_url': complex['url'],
                'complex_addr': self._get_complex_addr(complex),
            })
            yield request

    def genplan_page(self, response):
        """
        Parse the «genplan» output — PIK uses it to render fancy
        buildings at the homepage of each complex.

        Pik has one extra catalog level — section. We call it «subcomplex» and use to build the address of the house — it contains no more sense.
        """
        try:
            data = json.loads(response.body_as_unicode())[0]['data']['sets_of_pathes']
        except TypeError:
            print('Bad data (no genplan?)', response.meta['complex_url'], json.loads(response.body_as_unicode())[0])
            return

        for subcomplex in data:
            request = Request(
                self.CHESS_PLAN_URL.format(
                    URL=URL,
                    complex_url=response.meta['complex_url'],
                    subcomplex_id=subcomplex['id'],
                ),
                callback=self.chessplan_page,
            )
            request.meta.update(response.meta)
            request.meta.update({
                'subcomplex_id': subcomplex['id'],
                'subcomplex_addr': request.meta['complex_addr'] + ' ' + subcomplex['title'] if request.meta['complex_addr'] is not None else None,
            })
            yield request

    def chessplan_page(self, response):
        """
        Parse the chessplan JSON. PIK uses it to render every house plans
        """
        data = json.loads(response.body_as_unicode())
        for section in data['sections']:
            floors = section['floors']
            if isinstance(floors, dict):
                floors = floors.items()
            else:
                floors = enumerate(floors)

            for floor_number, floor in floors:
                for appt in floor['flats']:
                    if 'title' not in appt['status'].keys():  # no appts here
                        continue

                    if appt['status']['title'].lower() in ['cвободна', 'забронирована']:
                        yield Item(
                            complex_name=response.meta['complex_name'],
                            complex_id=response.meta['complex_id'],
                            complex_url=URL + response.meta['complex_url'] + '/',
                            addr=response.meta['complex_addr'],

                            house_id=self._get_house_id(section),
                            house_name=section['name'],
                            house_url=URL + response.meta['complex_url'] + '/genplan/',

                            id=appt['id'],
                            floor=floor_number,
                            room_count=appt['roomQuantity'] if appt['roomQuantity'] not in ['С', 'C'] else 1,
                            is_studio=appt['roomQuantity'] in ['С', 'C'],
                            square=appt['wholeAreaBti'],
                            price=appt['wholePrice'],
                            plan_url=appt.get('planing', dict()).get('srcLayout'),
                        )

    def _parse_home_page(self, response) -> dict:
        """
        Parse the JSON contained right within the homepage HTML
        """
        script = response.css('script[async]').extract()[0]
        script = script.replace('<script type="application/javascript" async>', '')
        script = script.replace('</script>', '')
        script = script.replace('window.REDUX_INITIAL_STATE =', '')
        script = script.strip()
        script = re.sub(';$', '', script)

        return json.loads(script)['complexes']['complexesList']['main']

    def _get_house_id(self, section):
        """
        PIK shows no ID for «Секции», so we create our own ID by hashing the unique section name
        """
        return hashlib.md5(section['name'].encode('utf-8')).hexdigest()

    def _get_complex_addr(self, complex):
        if any(s.isdigit() for s in complex['address']):
            return complex['address']
