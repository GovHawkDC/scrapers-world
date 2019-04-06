import lxml.html
from pupa.scrape import Scraper, Person
from lxml import etree

class IndiaPersonScraper(Scraper):

    def scrape(self):

        # lower
        url = 'http://164.100.47.194/Loksabha/Members/AlphabeticalList.aspx'
        entry = self.get(url).content

        page = lxml.html.fromstring(entry)
        page.make_links_absolute(url)

        for tr in page.xpath('//table[contains(@class,"member_list_table")]/tr'):
            name = tr.xpath('td[2]/a[1]/@title')[0]
            bio = tr.xpath('td[2]/a[1]/@href')[0]
            photo_url = tr.xpath('td[2]/a[1]/img/@src')[0]
            party = tr.xpath('td[3]/text()')[0].strip()
            state = tr.xpath('td[4]/text()')[0].strip()
            member = Person(name=name,
                            role="member",
                            primary_org="lower",
                            party=party,
                            image=photo_url,
                            district=state)

            member.add_source('http://164.100.47.5/Newmembers/memberlist.aspx')
            yield member

        # upper
        url = 'http://164.100.47.5/Newmembers/memberlist.aspx'
        entry = self.get(url).content

        page = lxml.html.fromstring(entry)
        page.make_links_absolute(url)

        for tr in page.xpath('//table[@id="ContentPlaceHolder1_GridView2"]/tr')[1:]:
            name = tr.xpath('td[2]/font/a/text()')[0]
            party_abbr = tr.xpath('td[3]/font/text()')[0].strip()
            state = tr.xpath('td[4]/font/text()')[0].strip()

            member = Person(name=name,
                            role="member",
                            primary_org="upper",
                            party=party_abbr,
                            district=state)

            member.add_source('http://164.100.47.5/Newmembers/memberlist.aspx')
            yield member
