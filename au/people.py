
import csv
from pupa.scrape import Scraper, Person
from io import StringIO

import pytz

class AUPersonScraper(Scraper):

    ocds_by_name = {}

    def scrape(self):

        # self.ocds_by_name = get_ocds_by_name()

        yield self.scrape_lower()
        yield self.scrape_upper()

    def parse_row(self, row, chamber):
        print(row)

        display = '{} {}'.format(row['First Name'], row['Surname'])

        # TODO: map state to ocd
        # TODO: https://www.aph.gov.au/Senators_and_Members/Senators/Senators_by_service_expiry_date

        person = Person(
            name=display,
            district=row['State'],
            role='member',
            primary_org=chamber,
            gender=row['Gender'].lower(),
            party=row['Political Party'],
        )

        person.extras['given_name'] = row['First Name']
        person.extras['family_name'] = row['Surname']

        return person

    def scrape_lower(self):
        url = 'https://www.aph.gov.au/~/media/03%20Senators%20and%20Members/' \
              'Address%20Labels%20and%20CSV%20files/StateRepsCSV.csv?la=en'

        csvfile = self.get(url)
        rows = csv.DictReader(StringIO(csvfile.text))

        for row in rows:
            person = self.parse_row(row, 'House of Representatives')

            person.add_source(
                url = 'https://www.aph.gov.au/Senators_and_Members/Members')
            yield person

    def scrape_upper(self):
        url = 'https://www.aph.gov.au/~/media/03%20Senators%20and%20Members/' \
              'Address%20Labels%20and%20CSV%20files/allsenel.csv?la=en'
        csvfile = self.get(url)
        rows = csv.DictReader(StringIO(csvfile.text))

        for row in rows:
            person = self.parse_row(row, 'Senate')

            person.add_source(
                url = 'https://www.aph.gov.au/Senators_and_Members/Senators')
            yield person
