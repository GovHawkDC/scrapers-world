
import lxml.html
from pupa.scrape import Scraper, Person
from lxml import etree
import json
from .utils import get_all_pages, get_ocds_by_name
import pprint
import sys
import requests
import unidecode
import dateutil.parser
import pytz

class UKPersonScraper(Scraper):
    # http://lda.data.parliament.uk/commonsmembers.json?_pageSize=50
    # http://lda.data.parliament.uk/lordsmembers.json?_pageSize=50
    # http://lda.data.parliament.uk/members.json?_pageSize=500

    # http://data.parliament.uk/membersdataplatform/services/mnis/Department/0/Government/Current/
    # http://data.parliament.uk/membersdataplatform/services/mnis/HouseOverview/Commons/2012-01-01/

    # TODO: This looks like a better source...
    # http://data.parliament.uk/membersdataplatform/memberquery.aspx#outputs
    # http://data.parliament.uk/membersdataplatform/services/mnis/members/query/house=Commons/BasicDetails/
    # http://data.parliament.uk/membersdataplatform/services/mnis/members/query/House=Commons%7CIsEligible=true/Addresses/
    # http://data.parliament.uk/membersdataplatform/services/mnis/members/query/House=Commons%7CIsEligible=true/Addresses%7CConstituencies%7CStaff/

    # http://data.parliament.uk/membersdataplatform/services/mnis/ReferenceData/Constituencies/

    # get this (i think theres a way to get only current or on a date)
    # and use it to get the ordnance survey ID,
    # which can then be crossed reffed to OCD
    # http://data.parliament.uk/membersdataplatform/services/mnis/ReferenceData/Constituencies/
    # it's the <ONSCode> key

    ocds_by_name = {}
    genders = {'F': 'female', 'M': 'male'}
    houses = {'Commons': 'House of Commons', 'Lords': 'House of Lords'}

    def api_query(self, query):
        api_base = 'http://data.parliament.uk/membersdataplatform/services/mnis/'
        url = '{}{}'.format(api_base, query)
        # print(url)
        headers = {"accept": "application/json"}
        page = requests.get(url, headers=headers)
        # print(page.content)
        return json.loads(page.content)

    def process_date(self, date):
        date = dateutil.parser.parse(date)
        date = date.replace(tzinfo=pytz.UTC)
        return date

    def scrape(self):

        self.ocds_by_name = get_ocds_by_name()

        yield self.scrape_lower()
        yield self.scrape_upper()

    def process_person(self, member):
        # print(member)

        if member['Party']:
            party = member['Party']['#text']
        else:
            party = None

        person = Person(
            name=member['DisplayAs'],
            district=member['MemberFrom'],
            role='member',
            primary_org=self.houses[member['House']],
            gender=self.genders[member['Gender']],
            party=party,
            start_date=self.process_date(member['CurrentStatus']['StartDate']),
        )

        if type(member['PreferredNames']['PreferredName']) == list:
            names = member['PreferredNames']['PreferredName'][0]
        else:
            names = member['PreferredNames']['PreferredName']

        person.extras['given_name'] = names['Forename']
        person.extras['family_name'] = names['Surname']

        if type(member['DateOfBirth']) is str:
            person.birth_date = self.process_date(member['DateOfBirth'])

        return person

    def scrape_lower(self):
        fragment = 'members/query/House=Commons%7CIsEligible=true/Addresses%7CConstituencies%7CStaff%7CPreferredNames/'
        members = self.api_query(fragment)

        for member in members['Members']['Member']:

            person = self.process_person(member)

            # we need the unidecode to remove special chars
            ascii_post = unidecode.unidecode(member['MemberFrom'].lower())
            person.extras['division_id'] = self.ocds_by_name[ascii_post]

            person.add_source(
                url = 'http://www.parliament.uk/mps-lords-and-offices/mps/')
            yield person

    def scrape_upper(self):
        web_url='http://www.parliament.uk/mps-lords-and-offices/lords/'

        fragment = 'members/query/House=Lords%7CIsEligible=true/Addresses%7CConstituencies%7CStaff%7CPreferredNames/'
        members = self.api_query(fragment)

        for member in members['Members']['Member']:

            person = self.process_person(member)
            person.add_source(
                url = 'http://www.parliament.uk/mps-lords-and-offices/lords/')
            yield person

    def add_extras(self, member, person):
        person.extras = {'family_name':member['familyName']['_value'],
                         'sort_name':member['familyName']['_value'],
                        }

        if 'birth_date' in member:
            person.birth_date = member['birthDate']['_value']

        if 'death_date' in member:
            person.death_date = member['deathDate']['_value']

        if 'gender' in member:
            person.gender = member['gender']['_value']

        if 'givenName' in member:
            person.extras['given_name'] = member['givenName']['_value']

        if 'party' in member:
            person.extras['party'] = member['party']['_value']

        if 'twitter' in member:
            if member['twitter']['_value'][0:4] != 'http':
                member['twitter']['_value'] = 'https://twitter.com/{}'.format(member['twitter']['_value'])
            person.links.append({'note':'twitter', 'url': member['twitter']['_value']})

        if 'homepage' in member:
            person.links.append({'note':'Home Page', 'url':member['homepage']})

        return person
