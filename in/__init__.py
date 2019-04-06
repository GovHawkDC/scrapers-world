# coding: utf-8
#from opencivicdata.divisions import Division
from pupa.scrape import Organization
from pupa.scrape import Jurisdiction

from datetime import datetime

from .people import IndiaPersonScraper
from .bills import IndiaBillScraper

class India(Jurisdiction):
    classification = 'legislature'
    division_id = 'ocd-division/country:in'
    division_name = 'India'
    name = 'Parliament of India'
    url = 'http://parliamentofindia.nic.in/'
    parties = [
        {'name': 'National Democratic Alliance'},
        {'name': 'United Progressive Alliance'},
        {'name': 'Bharatiya Janata Party'},
    ]
    scrapers = {
        "people": IndiaPersonScraper,
        "bills": IndiaBillScraper,
    }
    legislative_sessions = [
        {"identifier":"2017",
         "name":"2017 Session",
         "start_date": "2017-01-01",
         "end_date": "2017-12-31"},
        {"identifier":"2018",
         "name":"2018 Session",
         "start_date": "2018-01-01",
         "end_date": "2018-12-31"},
        {"identifier":"2019",
         "name":"2019 Session",
         "start_date": "2019-01-01",
         "end_date": "2019-12-31"},
    ]


    def get_organizations(self):
        parliament = Organization(self.name, classification=self.classification)
        yield parliament

        upper = Organization('Rajya Sabha', classification='upper', parent_id=parliament)
        lower = Organization('Lok Sabha', classification='lower', parent_id=parliament)

        yield upper
        yield lower
