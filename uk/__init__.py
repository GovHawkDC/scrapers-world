# coding: utf-8
import csv
import json
import requests

from pupa.scrape import Organization
from pupa.scrape import Jurisdiction

from datetime import datetime

from .people import UKPersonScraper
from .bills import UKBillScraper

from .utils import get_pcons


class UK(Jurisdiction):
    classification = 'legislature'
    division_id = 'ocd-division/country:uk'
    division_name = 'United Kingdom'
    name = 'Parliament of the United Kingdom'
    url = 'http://www.parliament.uk/'
    parties = [
        {'name': 'Conservative Party'},
    ]
    scrapers = {
        "people": UKPersonScraper,
        "bills": UKBillScraper,
    }

    # http://lda.data.parliament.uk/sessions.json
    legislative_sessions = [
        {"identifier": "2016-2017",
         "name": "2016-2017 Session",
         "start_date": "2016-05-18"}
    ]

    def get_organizations(self):

        parliament = Organization(
            self.name, classification=self.classification)
        yield parliament

        upper = Organization(
            'House of Lords', classification='upper', parent_id=parliament)
        lower = Organization('House of Commons',
                             classification='lower', parent_id=parliament)

        pcons = utils.get_pcons()

        for pcon in pcons:
            lower.add_post(label=pcon['name'],
                           role='member', division_id=pcon['id'])

        yield upper
        yield lower
