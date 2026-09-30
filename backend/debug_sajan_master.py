import xml.etree.ElementTree as ET
f = '../busy(26-27)master.DAT'
tree = ET.parse(f)
root = tree.getroot()
for acc in root.findall('.//Accounts/Account'):
    name = acc.findtext('Name')
    if name and 'SAJANBHAI' in name:
        for child in acc:
            print(f"{child.tag}: {child.text}")
