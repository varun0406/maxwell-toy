import xml.etree.ElementTree as ET
from decimal import Decimal

files = ["../busy-24-25a.DAT", "../busy-25-26..DAT", "../busy 26-27....DAT"]
alloc_amt = Decimal('0')
unalloc_amt = Decimal('0')

for file in files:
    try:
        root = ET.parse(file).getroot()
        account_map = {}
        for acc in root.findall('.//AccountMaster'):
            code = acc.findtext('MasterCode') or acc.findtext('tmpMasterCode1')
            name = acc.findtext('Name')
            if code and name:
                account_map[code.strip()] = name.strip()
                
        def get_party_name(element):
            name1 = element.findtext('MasterName1')
            if name1: return name1
            name2 = element.findtext('AccountName')
            if name2: return name2
            code1 = element.findtext('MasterCode1')
            if code1 and code1.strip() in account_map: return account_map[code1.strip()]
            tcode1 = element.findtext('tmpMasterCode1')
            if tcode1 and tcode1.strip() in account_map: return account_map[tcode1.strip()]
            tcode = element.findtext('tmpAccCode')
            if tcode and tcode.strip() in account_map: return account_map[tcode.strip()]
            return ""

        for v in root.findall(".//Receipt"):
            for acc in v.findall(".//AccDetail"):
                name = get_party_name(acc)
                if "DEEPAK" in name.upper():
                    amt = Decimal(acc.findtext("AmtMainCur") or '0')
                    br = acc.find("BillRefs")
                    if br is not None and len(br.findall("BillDetails")) > 0:
                        mapped = Decimal('0')
                        for b in br.findall("BillDetails"):
                            mapped += Decimal(b.findtext("Value1") or '0')
                        alloc_amt += mapped
                        unalloc_amt += (amt - mapped)
                    else:
                        unalloc_amt += amt
    except Exception as e:
        pass

print(f"Deepak Allocated: {alloc_amt}")
print(f"Deepak Unallocated: {unalloc_amt}")
