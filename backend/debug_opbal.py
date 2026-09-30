import xml.etree.ElementTree as ET
party_name = ' '.join('SAJANBHAI ( V I P )'.split())
f = '../busy(24-25).DAT'

tree = ET.parse(f)
root = tree.getroot()
for acc in root.findall('.//Accounts/Account'):
    name = acc.findtext('Name')
    if name and 'SAJANBHAI' in name:
        print(f"24-25 SAJANBHAI OPBal: {acc.findtext('OPBal')}")
        print(f"24-25 SAJANBHAI PYBal: {acc.findtext('PYBal')}")

f2 = '../busy(25-26).DAT'
tree2 = ET.parse(f2)
root2 = tree2.getroot()
for acc in root2.findall('.//Accounts/Account'):
    name = acc.findtext('Name')
    if name and 'SAJANBHAI' in name:
        print(f"25-26 SAJANBHAI OPBal: {acc.findtext('OPBal')}")
        
