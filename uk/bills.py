import lxml.html
from pupa.scrape import Scraper, Bill, VoteEvent
from lxml import etree
from datetime import datetime
import pytz
from .utils import get_all_pages
import pprint

# http://lda.data.parliament.uk/meta/bills/_id.json
# http://lda.data.parliament.uk/bills.json?session.displayName=2016-2017&_view=description&_pageSize=10&_page=0&originatingLegislature.prefLabel=House%20of%20Lords

class UKBillScraper(Scraper):
    api_base = 'http://lda.data.parliament.uk/'
    tz = pytz.timezone('Europe/London')

    def scrape(self,session=None,chamber=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber else ['upper', 'lower']
        for chamber in chambers:
            print(chamber)
            yield from self.scrape_chamber(session, chamber)

    def scrape_chamber(self,session,chamber):
        # By default the description view is good, 
        # but pulling a few additional fields will save us queries later
        additional_fields = ['billPublications.homePage',
                             'billPublications.contentType',
                             'billPublications.date',
                             'billPublications.publicationType',
                             'billAmendment.homePage',
                             'billAmendment.contentType',
                             'billAmendment.date',
                             'billAmendment.publicationType',
                             'sponsors.legislature.prefLabel',
                             'sponsors.legislature.prefLabel',
                             'sponsors.member',
                             'sponsors.sponsorPrinted',
                             'billStage.billStageType.title',
                             'billStage.billStage.label',
                             'billStage.billStageType.label',
                             'billStage.billStageType.legislature.prefLabel',
                             'billStage.legislature',
                             'billStage.billStageSitting.date',
                             'billStage.billStageSitting.provisional']

        # fields are collapsed into a single comma seperated url argument
        additional_fields = ','.join(additional_fields)

        url = "{}bills.json".format(self.api_base)
        url_args = {'session.displayName':session,
                    '_properties':additional_fields,
                    '_view':'description'}
        if 'upper' == chamber:
            url_args['originatingLegislature.prefLabel'] = 'House of Lords'
        elif 'lower' == chamber:
            url_args['originatingLegislature.prefLabel'] = 'House of Commons'

        pages = get_all_pages(url, url_args)

        for page in pages:
            print("\n")
            print(page)
            page['title'] = page['title'].replace(' [HL]', '')
            bill = Bill(identifier=page['identifier']['_value'],
                        legislative_session=session,
                        title=page['label']['_value'],
                        classification='bill')
            
            
            if 'sponsors' in page:
                for sponsor in page['sponsors']:
                    if 'primary' in sponsor and sponsor['primary'] == 'True':
                        bill.add_sponsorship(name=str(sponsor['sponsorPrinted']), 
                                            classification="Primary",
                                            entity_type="person",
                                            primary=True)
                    else:
                            bill.add_sponsorship(name=str(sponsor['sponsorPrinted']), 
                                            classification="Secondary",
                                            entity_type="person",
                                            primary=False)                      
            if 'billPublications' in page:
                for version in page['billPublications']:
                    # Occasionally they publish version metadata with no link
                    if 'homePage' in version:
                        if self.classify_version(version) == 'version':
                            bill.add_version_link(note=version['label']['_value'],
                                                url=version['homePage'],
                                                date=version['date']['_value'],
                                                media_type=version['contentType'],
                                                on_duplicate='ignore')
                        else:
                            bill.add_document_link(note=version['label']['_value'],
                                                url=version['homePage'],
                                                date=version['date']['_value'],
                                                media_type=version['contentType'],
                                                on_duplicate='ignore')
            if 'billStages' in page:
                for action in page['billStages']:
                    self.scrape_actions(bill, page)

            bill.add_source(page['homePage'])
            yield bill

    def classify_version(self, version):
        if 'publicationType' in version:
            if version['publicationType']['_value'] == 'Bill' or version['publicationType']['_value'] == 'Amendment Paper':
                return 'version'
            else:
                return 'document'
        else:
            if 'bill' in version['label']['_value'].lower():
                return 'version'
        return 'document'

    def scrape_actions(self, bill, page):        
        for action in page['billStages']:
            print("\n")
            pprint.pprint(action)

            if 'legislature' in action['billStageType']:
                if action['billStageType']['legislature'][0]['prefLabel']['_value'] == 'House of Commons':
                    chamber = 'lower'
                elif action['billStageType']['legislature'][0]['prefLabel']['_value'] == 'House of Lords':
                    chamber = 'upper'
            else:
                chamber = 'executive'
            
            # Note: Not every stage is represented in this list, the full is is at:
            # http://lda.data.parliament.uk/billstagetypes.json?_pageSize=200
            # 
            # https://www.gov.uk/guidance/legislative-process-taking-a-bill-through-parliament
            # https://www.publications.parliament.uk/pa/ld/ldcomp/compso2013/10.htm
            classification_map = {
                '1st reading':'reading-1',
                '2nd reading':'reading-2',
                '3rd reading':'reading-3',
                'Bill reintroduced':'amendment-introduction',
                'Bill withdrawn':'withdrawal',
                # http://www.parliament.uk/site-information/glossary/carry-over-motions-bills/
                'Carry-over motion':'other',
                # http://www.parliament.uk/site-information/glossary/negative-procedure/
                'Committee negatived':'other',
                'Commons Examiners':'other',
                'Consequential consideration':'other',
                'Consideration of Commons amendments':'other',
                'Consideration of Lords amendments':'other',
                'Examination for compliance with Standing Orders':'other',
                'Guillotine motion':'other',
                'Legislative Grand Committee':'other',
                'Motion to revive Bill':'other',
                'Motion to suspend Bill till next session approved':'deferral',
                'Motion to suspend Bill till next session considered':'other',
                'Order of Commitment discharged':'referral-committee',
                'Petition to introduce a Private Bill presented to Parliament':'introduction',
                'Reconsideration':'other',
                'Report stage':'other',
                'Royal Assent':'executive-signature',
                'Second reading committee':'reading-2',
                'motion to revive Bill':'other',
            }

            # sometimes they publish actions w/out a date
            if action['billStageSittings'][0]['date']['_value']:
                if action['billStageType']['label']['_value'] in classification_map:
                    action_class = classification_map[action['billStageType']['label']['_value']]
                else:
                    action_class = 'other'

                if action_class != 'other':
                    act = bill.add_action(description=action['billStageType']['title'],
                                    chamber=chamber,
                                    date=action['billStageSittings'][0]['date']['_value'],
                                    classification=action_class, #see note about allowed classifications
                                    )
                else:
                    act = bill.add_action(description=action['billStageType']['title'],
                                    chamber=chamber,
                                    date=action['billStageSittings'][0]['date']['_value'],
                                    )               