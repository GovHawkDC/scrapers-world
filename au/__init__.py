# coding: utf-8
import csv
import json
import requests

from pupa.scrape import Organization
from pupa.scrape import Jurisdiction

from datetime import datetime

from .people import AUPersonScraper
from .bills import AUBillScraper

class AU(Jurisdiction):
    classification = 'legislature'
    division_id = 'ocd-division/country:au'
    division_name = 'Australia'
    name = 'Parliament of Australia'
    url = 'https://www.aph.gov.au/'

    scrapers = {
        "people": AUPersonScraper,
        "bills": AUBillScraper,
    }

    legislative_sessions = [
        {"identifier": "45",
         "name": "45th Parliament",
         "start_date": "2016-08-30",
         "end_date": "2019-12-31"}
    ]

    def get_organizations(self):

        parliament = Organization(
            self.name, classification=self.classification)
        yield parliament

        upper = Organization(
            'Senate', classification='upper', parent_id=parliament)
        lower = Organization('House of Representatives',
                             classification='lower', parent_id=parliament)

        # pcons = utils.get_pcons()

        # for pcon in pcons:
        #     lower.add_post(label=pcon['name'],
        #                    role='member', division_id=pcon['id'])

        yield upper
        yield lower
