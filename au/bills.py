import pytz

import lxml.html
import urllib.parse as urlparse

from pupa.scrape import Scraper, Bill, VoteEvent
from lxml import etree
from datetime import datetime

class AUBillScraper(Scraper):
    tz = pytz.timezone('Australia/Sydney')

    RESULTS = None

    CHAMBERS = {
        'House of Representatives': 'lower',
        'Senate': 'upper'
    }

    def scrape(self,session=None, chamber=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_bills(session, chamber)

    def scrape_bills(self,session, chamber):
        # self.jurisdiction.legislative_sessions[session].
        page = self.search_results(session)

        for row in page.xpath('//ul[contains(@class,"search-filter-results")]/li/div[@class="row"]'):
            bill_url = row.xpath('.//h4/a/@href')[0]

            bill_chamber = self.dd(row, 'Chamber')

            if self.CHAMBERS[bill_chamber] == chamber:
                # print(bill_url, bill_chamber)
                yield from self.scrape_bill(session, chamber, bill_url)

    def scrape_bill(self, session, chamber, url):
        html = self.get(url).content
        page = lxml.html.fromstring(html)

        title = page.xpath('//div[@id="main_0_header"]//h1/text()')[0].strip()

        parsed = urlparse.urlparse(url)
        bill_id = urlparse.parse_qs(parsed.query)['bId'][0]

        portfolio = self.dd(page, 'Portfolio')
        orig_house = self.dd(page, 'Originating house')
        print("TEST")
        print(bill_id, title, portfolio, orig_house)

        bill = Bill(bill_id,
                    legislative_session=session,
                    chamber=chamber,
                    title=title,
                    classification='bill')


        sponsor = self.dd(page, 'Sponsor(s)')
        if sponsor:
            bill.add_sponsorship(name=sponsor,
                                classification="Primary",
                                entity_type="person",
                                primary=True)

        self.scrape_bill_versions(page, bill)
        self.scrape_bill_documents(page, bill)

        bill.add_source(url)


            # act = bill.add_action(description=action['billStageType']['title'],
            #                 chamber=chamber,
            #                 date=action['billStageSittings'][0]['date']['_value'],
            #                 classification=action_class, #see note about allowed classifications
            #                 )

        yield bill

    def scrape_bill_versions(self, page, bill):
        rows = page.xpath('//table[contains(@class,"bill-docs")][1]/tbody/tr')
        for row in rows:
            version_name = row.xpath('td[1]/ul/li/text()')[0].strip()
            for link in row.xpath('td[2]/a'):
                link_type = link.xpath('img/@alt')[0]
                version_url = link.xpath('@href')[0]
                if 'Word' in link_type:
                    bill.add_version_link(note=version_name,
                                        url=version_url,
                                        media_type='application/msword',
                                        on_duplicate='ignore')
                elif 'PDF' in link_type:
                    bill.add_version_link(note=version_name,
                                        url=version_url,
                                        media_type='application/pdf',
                                        on_duplicate='ignore')
                elif 'HTML' in link_type:
                    bill.add_version_link(note=version_name,
                                        url=version_url,
                                        media_type='text/html',
                                        on_duplicate='ignore')

    def scrape_bill_documents(self, page, bill):
        rows = page.xpath('//table[contains(@class,"bill-docs")][2]/tbody/tr')
        for row in rows:
            version_name = row.xpath('td[1]/ul/li/text()')[0].strip()
            for link in row.xpath('td[2]/a'):
                link_type = link.xpath('img/@alt')[0]
                version_url = link.xpath('@href')[0]
                if 'Word' in link_type:
                    bill.add_document_link(note=version_name,
                                        url=version_url,
                                        media_type='application/msword',
                                        on_duplicate='ignore')
                elif 'PDF' in link_type:
                    bill.add_document_link(note=version_name,
                                        url=version_url,
                                        media_type='application/pdf',
                                        on_duplicate='ignore')
                elif 'HTML' in link_type:
                    bill.add_document_link(note=version_name,
                                        url=version_url,
                                        media_type='text/html',
                                        on_duplicate='ignore')

    # since we're not scraping by chamber, at least
    # cache the search results page so we don't pull it twice
    def search_results(self, session):
        if self.RESULTS is not None:
            return self.RESULTS

        url = 'https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_before_Parliament'
        params = {
            'pnu': session,
            'pnuH': session,
            'ps': 500,
            'q': '',
        }

        html = self.get(url, params=params).content
        page = lxml.html.fromstring(html)

        page.make_links_absolute(url)

        self.RESULTS = page
        return page

    # many pages have <dt>Header</dt><dd>Data</dd>
    # Given Header, return Data
    def dd(self, page, header):
        expr = '//dt[text()="{}"]/following-sibling::dd/text()'.format(header)
        print(expr)
        if page.xpath(expr):
            dd = page.xpath(expr)[0]
            return dd.strip()
        else:
            return ''