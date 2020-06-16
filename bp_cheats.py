from bs4 import BeautifulSoup
import requests
import re
import json
# from datetime import datetime
from random import randint, randrange
import time
from urllib.parse import quote
import logging
import webbrowser

#from test import jprint

logging.basicConfig(filename='bp.log', filemode='w',
                    format='%(levelname)s %(asctime)s %(funcName)s %(module)s %(message)s', datefmt="%H:%M:%S",
                    level=logging.INFO)
logging = logging.getLogger(__name__)


def write_json(data, file_name):
    with open(file_name, 'w') as json_file:
        json.dump(data, json_file, sort_keys=False)


def load_json(file_name):
    with open(file_name) as json_file:
        return json.load(json_file)


def get_item_names_from_site(out_path='json/raw_items.txt'):
    """
    bp have the huge json list of all items, so this fun will get it
    """
    page = requests.get('https://backpack.tf/pricelist')
    soup = BeautifulSoup(page.content, 'html.parser')

    p = re.compile('var jsonItems = (.*?);')
    script = soup.find_all('script')[5].string
    m = p.findall(script)
    items = json.loads(m[0])
    write_json(items, out_path)


def filter_items(min_price=5, max_price=200, in_path='json/raw_items.txt', out_path='json/filt_items.txt'):
    """
    Get items within sertain price, and remove ones which have been updated (price)
    Prices defined if refs
    """
    items = load_json(in_path)
    items = sorted(items, key=lambda i: (i['last_update']), reverse=True)

    n = len(items)
    print(f'Number of loaded items: {n}')
    tolerance = 0  # spicify in seconds. Why tho

    print(
        f'Removing items that was updated in recent {tolerance / 86400:.0f} days, price lower than {min_price} ref or higher than {max_price} ref')
    # items = list(filter(lambda i: i['last_update'] - tolerance > 0, items))
    items = [i for i in items if
             i['last_update'] + tolerance < time.time() and i['price'] > min_price and i['price'] < max_price]

    ignore_str = ["Strangifier", "Collector's", "Crate"]
    print(f'Also removing items with {ignore_str} in it')
    check_str = lambda s: not any(ig in s for ig in ignore_str)
    items = [i for i in items if check_str(i['full_name'])]

    print(f'Removed {n - len(items)} items')
    write_json(items, out_path)
    return out_path


def create_url(item):
    """
    Create url from item name
    """
    base_url = 'https://backpack.tf/stats/'
    tradeble = '/Tradable/'
    craftable = ['Non-Craftable', 'Craftable']
    item_name = quote(item['item_name'], safe='')
    item_quality_str = re.findall(r'Strange|Genuine|Vintage|Haunted|Unique', item['full_name'])
    item_craft = craftable[item['craftable']]
    item_quality = ('Unique' if item_quality_str == [] else '%20'.join(item_quality_str)) + '/'

    url = base_url + item_quality + item_name + tradeble + item_craft
    return url


def parse_prices(prices_text):
    """
    Extract value and currency from str listing prices
    '0.77 keys' -> [[0.77, 'keys']]
    """
    currency = [re.findall(r'[a-zA-Z]+', price)[0] for price in prices_text]  # from '0.77 keys' extract keys
    price = [re.match(r'\d+(\.\d+)?(?=\s+[a-zA-Z]+)', price)[0] for price in
             prices_text]  # from '0.77 keys' extract 0.77

    return list(zip(currency, price))


def get_sugested_price(j_item, key_price_bp=44):
    """
    Extract suggested price from item page in [ref_price, key_price] format
    """
    ref_price = ('ref', j_item['price'])
    prices = j_item['price_text'] + ', ' + j_item['price_currencies']  # 43.66–43.77 ref, 0.99 keys, $1.75
    '''key_price = re.findall(r'(\d+(\.\d+)) (keys)', prices)
    if key_price == [] or key_price[0][0] == '':
        key_price = float(j_item['price']) / key_price_bp
    else:
        key_price = key_price[0][0]'''
    key_price = float(j_item['price']) / key_price_bp
    key_price = ('keys', key_price)
    s = [ref_price, key_price]

    return s


def find_dif_2(prices, suggested_price, key_price_bp=44):
    """
    Calulate difference between lising and suggested in refs
    """
    ref_price = float(suggested_price[0][1])
    key_price = float(suggested_price[1][1])
    res = []
    res_per = []
    for price in prices:
        if price[0] == 'ref':
            p = float(price[1]) - ref_price
            res.append(('ref', p))
            res_per.append((1 + (p / ref_price)))
        else:
            p = float(price[1]) - key_price
            res.append(('ref', p * key_price_bp))
            res_per.append(((1 + (p / key_price))))

    return res, res_per


def tulp_str(tulp):
    """
    Psyho way to convert float to .2 precision float
    """
    t = [' '.join([str(('{:.2f}'.format(float(tul[1])))), tul[0]]) for tul in tulp]
    return ', '.join(map(str, t))


def floats_str(arr):
    return ', '.join(format(x, ".2f") for x in arr)


def check_item(j_item, key_price_bp, warn=None):
    url = create_url(j_item)
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser', from_encoding="iso-8859-1")
    listings = soup.find_all('div', {'data-listing_intent': 'sell'})
    prices_text = [listing.findChild("div", {"class": "tag"}).span.text for listing in listings]

    prices = parse_prices(prices_text)
    suggested_price = get_sugested_price(j_item)
    dif, dif_per = find_dif_2(prices, suggested_price, key_price_bp)

    base_dict = {'Item_name': j_item['full_name'],
                 'bp_price_ref': float(suggested_price[0][1]),
                 'bp_price_key': float(suggested_price[1][1]),
                 'listing_prices': tulp_str(prices),
                 'link': url,
                 }

    if len(dif) > 0:
        base_dict['delta'] = tulp_str(dif)
        base_dict['perc'] = floats_str(dif_per)
        base_dict['delta_min'] = dif[0][1]
    else:
        base_dict['Low number of listings'] = ''

    if warn is not None and len(dif) > 1:
        if dif_per[1] - dif_per[0] > warn and dif_per[0] < 1.1:
            print('This might be interesting..')
            # webbrowser.open(url)
            #jprint(base_dict)
            print(json.dumps(base_dict, indent=1))
    '''else:
        logging.info(json.dumps(base_dict, sort_keys=False, indent=2))'''
    return base_dict


def get_random_item():
    items = load_json('json/filt_items.txt')
    item = items[randint(0, len(items))]
    print(item['full_name'])
    return item


def extract_items(items, key_price_bp=44., warn=None, out_path='json/result.txt'):
    n = len(items)
    result = []
    errors = 0
    while len(items) > 0:
        time.sleep(randint(5, 25) / 10000)
        try:
            i = randint(0, len(items))
            print('Extracting info about "' + items[i][
                'full_name'] + f'". {len(items)} items left, {(1 - (len(items) / n)) * 100:.2f}% completed')
            r = {"Item name": items[i]['full_name'],
                 "There was an error": "Check it manually.."}
            try:
                r = check_item(items.pop(i), key_price_bp, warn=warn)
            except Exception as e:
                print(e)
                errors += 1
                print('oof')   # best error handling
            result.append(r)
        except:
            errors += 1
            print('error')
            continue

    print(f'Number of errors: {errors}')
    write_json(result, out_path)


def fitler_items_by_val(items, min=0, max=10 ** 1000):
    return [i for i in items if i.get('bp_price_ref') > min and i.get('bp_price_ref') < max]


def filter_items_by_perc(items, filter_perc_value=5):
    result = [i for i in items if (i.get('perc') is not None and (float(
        i.get('perc').split(', ')[0]) < filter_perc_value))]  # keep values if delta pers are nmore then .8
    return result


def sort_items_by_val(items):
    return sorted(items, key=lambda k: k.get('bp_price_ref') if k.get(
        'bp_price_ref') is not None else 0)  # sort by delta and then price


def sort_items_by_perc(items):
    return sorted(items, key=lambda k: float(k.get('perc').split(', ')[0]) if k.get(
        'perc') is not None else 0)  # sort by delta and then price


def remove_items_wo_price(items):
    return [i for i in items if i.get('delta') is not None]  # remove items wothout price


if __name__ == "__main__":
    get_item_names_from_site()
    filt_path = filter_items()
    items = load_json(filt_path)
    extract_items(items, key_price_bp=50, warn=0.4)

    minim, maxim = 0, 10 * 100000
    perc = 0.81

    items = load_json('json/result.txt')
    result = items
    result = remove_items_wo_price(items)
    # result = filter_items_by_perc(items, perc)
    # result = fitler_items_by_val(result, min=minim, max=maxim)
    result = sort_items_by_val(result)

    result = sort_items_by_perc(result)

    write_json(result, 'json/sorted_val_.json')  # f'json/result_sorted_min{minim}_max{maxim}_perc{perc}.json'

    items = load_json('json/result.txt')
    result = remove_items_wo_price(items)
    result = sort_items_by_perc(result)

    write_json(result, 'json/sorted_perc.json')

    print('done')
