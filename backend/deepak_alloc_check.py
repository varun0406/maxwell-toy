import xml.etree.ElementTree as ET
from decimal import Decimal

files = ["../busy-24-25a.DAT", "../busy-25-26..DAT", "../busy 26-27....DAT"]
alloc_amt = Decimal('0')
unalloc_amt = Decimal('0')

for file in files:
    try:
        root = ET.parse(file).getroot()
        for v in root.findall(".//Receipt"):
            for acc in v.findall(".//AccDetail"):
                name = acc.findtext("AccountName") or acc.findtext("MasterName1") or acc.findtext("tmpMasterCode1") or ""
                if "DEEPAK" in name.upper() or "1138" in name: # 1138 is his tmpMasterCode1 maybe? I will just check DEEPAK for now
                    pass # wait I need the account map for deepakbhai
    except Exception as e:
        pass
