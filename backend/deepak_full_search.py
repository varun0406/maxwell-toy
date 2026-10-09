import xml.etree.ElementTree as ET
from decimal import Decimal

files = [
    '/home/varun/Documents/maxwellMobAcc/busy-24-25a.DAT',
    '/home/varun/Documents/maxwellMobAcc/busy-25-26..DAT',
    '/home/varun/Documents/maxwellMobAcc/busy 26-27....DAT'
]

def clean(val):
    return ' '.join((val or '').split())

def is_deepak(name):
    if not name: return False
    n = name.upper()
    return 'DEEPAK' in n

account_map = {}

for file in files:
    try:
        tree = ET.parse(file)
        root = tree.getroot()
        
        # Build account map
        for acc in root.findall('.//AccountMaster'):
            code = clean(acc.findtext('MasterCode'))
            code1 = clean(acc.findtext('tmpMasterCode1'))
            name = clean(acc.findtext('Name'))
            if code and name: account_map[code] = name
            if code1 and name: account_map[code1] = name
            
        def get_party_name(element):
            name1 = clean(element.findtext('MasterName1'))
            if name1: return name1
            name2 = clean(element.findtext('AccountName'))
            if name2: return name2
            code1 = clean(element.findtext('MasterCode1'))
            if code1 and code1 in account_map: return account_map[code1]
            tcode1 = clean(element.findtext('tmpMasterCode1'))
            if tcode1 and tcode1 in account_map: return account_map[tcode1]
            tcode = clean(element.findtext('tmpAccCode'))
            if tcode and tcode in account_map: return account_map[tcode]
            return None

        found_names = set()
        
        # Look in Sales, Receipts, etc.
        for v in root.findall('.//Sale'):
            party = get_party_name(v)
            if party and is_deepak(party): found_names.add(party)
        for v in root.findall('.//SaleReturn'):
            party = get_party_name(v)
            if party and is_deepak(party): found_names.add(party)
        for v in root.findall('.//Receipt'):
            for acc in v.findall('.//AccDetail'):
                party = get_party_name(acc)
                if party and is_deepak(party): found_names.add(party)
                
        if found_names:
            print(f"Names containing DEEPAK in {file}: {found_names}")

    except Exception as e:
        print(f"Error in {file}: {e}")

