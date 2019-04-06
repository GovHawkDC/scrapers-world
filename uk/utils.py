import json
import requests
import csv

def get_all_pages(url, url_args={}):
    return_val = []
    arguments = {'_pageSize':500,
                 '_page':0}
    arguments.update(url_args)
    page = requests.get(url, params=arguments)
    json_obj = json.loads(page.content)
    return_val = json_obj['result']['items']

    while 'next' in json_obj['result']:
        # the next url doesn't keep our page size, so tack it on
        url = "{}&_pageSize=500".format(json_obj['result']['next'])
        page = requests.get(url)
        json_obj = json.loads(page.content)
        return_val = return_val + json_obj['result']['items']

    return return_val

def get_ocds():
    # First we grab the OCD ids file,
    # then we can match it up based on GSS codes
    ocd_url = 'https://raw.githubusercontent.com/opencivicdata/ocd-division-ids/master/identifiers/country-uk.csv'

    ocds = requests.get(ocd_url).text

    ocds = csv.DictReader(ocds.splitlines())
    return ocds


def get_ocds_by_gss():
    ocds = get_ocds()

    ocds_by_gis = {}

    for ocd in ocds:
        ocds_by_gis[ocd['gss_code']] = ocd['id']

    return ocds_by_gis

def get_ocds_by_name():
    ocds = get_ocds()

    ocds_by_name = {}

    for ocd in ocds:
        ocds_by_name[ocd['name'].lower()] = ocd['id']

    return ocds_by_name

'''
Get all Parliamentary Constituencies (UK Lower House)
'''
def get_pcons():
    ocds = get_ocds()
    # or '/spc:' in ocd['id'] or '/nawc:' in ocd['id']
    pcons = (ocd for ocd in ocds if '/pcon:' in ocd['id'])
    return pcons