import pytz
import re
import lxml.html
import urllib.parse as urlparse

from pupa.scrape import Scraper, Bill, VoteEvent
from lxml import etree
from datetime import datetime


class AUBillScraper(Scraper):
    _TZ = pytz.timezone('Australia/Sydney')

    RESULTS = None

    CHAMBERS = {
        'House of Representatives': 'lower',
        'Senate': 'upper'
    }


    action_classifiers = [
        ('Introduced and read a first time', ['introduction', 'reading-1']),
        ('Second reading agreed to', ['reading-2']),
        ('Third reading agreed to', ['reading-3']),
        ('Assent', ['became-law']),
    ]


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
                yield from self.scrape_bill(session, chamber, bill_url)

    def scrape_bill(self, session, chamber, url):
        html = self.get(url).content
        page = lxml.html.fromstring(html)

        title = page.xpath('//div[@id="main_0_header"]//h1/text()')[0].strip()

        parsed = urlparse.urlparse(url)
        bill_id = urlparse.parse_qs(parsed.query)['bId'][0]

        portfolio = self.dd(page, 'Portfolio')
        orig_house = self.dd(page, 'Originating house')
        print(bill_id, title, portfolio, orig_house)

        bill_chamber = self.CHAMBERS[orig_house]

        bill = Bill(bill_id,
                    legislative_session=session,
                    chamber=bill_chamber,
                    title=title,
                    classification='bill')


        sponsor = self.dd(page, 'Sponsor(s)')
        if sponsor:
            bill.add_sponsorship(name=sponsor,
                                classification="Primary",
                                entity_type="person",
                                primary=True)

        self.scrape_bill_actions(page, bill)
        self.scrape_bill_versions(page, bill)
        self.scrape_bill_documents(page, bill)

        bill.add_source(url)

        yield bill

    def scrape_bill_versions(self, page, bill):
        # careful, the parens are relevant here, otherwise we get amendments too on
        # https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_Search_Results/Result?bId=s1042
        rows = page.xpath('(//table[contains(@class,"bill-docs")])[1]/tbody/tr')
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

    def scrape_bill_actions(self, page, bill):
        house_rows = page.xpath('//table[@class="fullwidth" and '
                                './/th[contains(string(.), "House of Representatives")]]')
        if house_rows:
            self.scrape_actions_table(house_rows[0], bill, 'lower')

        senate_rows = page.xpath('//table[@class="fullwidth" and '
                                './/th[contains(string(.), "Senate")]]')

        if senate_rows:
            self.scrape_actions_table(senate_rows[0], bill, 'upper')

        executive_rows = page.xpath('//table[@class="fullwidth" and '
                                './/span[contains(string(.), "Finally")]]')
        if executive_rows:
            self.scrape_actions_table(executive_rows[0], bill, 'executive')

    def scrape_actions_table(self, page, bill, chamber):
        rows = page.xpath('tbody/tr')
        for row in rows:
            action_text = row.xpath('td[1]/span/text()')[0].strip()
            action_date = row.xpath('td[2]/text()')[0].strip()
            action_date = self._TZ.localize(
                datetime.strptime(action_date, '%d %b %Y')
            )

            action_class = self.classify_action(action_text)

            # final passage is a special case; we need to make actions
            # (one per chamber) out of one statement
            if 'Finally passed both Houses' in action_text:
                for chamber in ['lower', 'upper']:
                    act = bill.add_action('Finally passed',
                        chamber=chamber,
                        date=action_date,
                        classification='passage',
                    )
            else:
                act = bill.add_action(action_text,
                    chamber=chamber,
                    date=action_date,
                    classification=action_class
                )

        # TODO: Test royal assent bills

    # since we're not scraping by chamber, at least
    # cache the search results page so we don't pull it twice
    def search_results(self, session):
        if self.RESULTS is not None:
            return self.RESULTS

        # page = 2
        url = 'https://www.aph.gov.au/Parliamentary_Business/Bills_Legislation/Bills_before_Parliament'
        params = {
            'pnu': session,
            'pnuH': session,
            'ps': 100,
            'q': '',
            'st': 2,
            'sr': 0,
            't': '',
            'ito': 1,
            'expand': 'False',
        }

        html = self.get(url, params=params).content
        page = lxml.html.fromstring(html)

        page.make_links_absolute(url)

        # TODO: pull max out of html, / 100, for i in 2..max scrape

        self.RESULTS = page
        return page

    # many pages have <dt>Header</dt><dd>Data</dd>
    # Given Header, return Data
    def dd(self, page, header):
        expr = '//dt[contains(text(),"{}")]/following-sibling::dd/text()'.format(header)
        if page.xpath(expr):
            dd = page.xpath(expr)[0]
            return dd.strip()
        else:
            return ''

    def classify_action(self, action):
        for regex, classification in self.action_classifiers:
            if re.match(regex, action):
                return classification
        return None
