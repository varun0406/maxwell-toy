import xml.etree.ElementTree as ET
import sys
sys.path.append("/home/varun/Documents/maxwellMobAcc/backend")
from app.database import SessionLocal
from app.models import Party

tree = ET.parse('/home/varun/Documents/maxwellMobAcc/busy-25-26..DAT')
root = tree.getroot()

found = 0
for rcpt in root.findall('.//Receipt'):
    for acc_det in rcpt.findall('.//AccDetail'):
        name = acc_det.findtext('MasterName1')
        if name and 'DEEPAK' in name.upper() and 'BHAV' in name.upper():
            print(f"Found receipt: {rcpt.findtext('VchNo')}")
            bill_refs = acc_det.find('BillRefs')
            print(f"BillRefs present: {bill_refs is not None}")
            if bill_refs is not None:
                for bd in bill_refs.findall('BillDetails'):
                    print("  - RefNo:", bd.findtext('RefNo'), "Value1:", bd.findtext('Value1'))
            else:
                print(ET.tostring(acc_det, encoding='unicode'))
            found += 1
            break
    if found > 2:
        break
