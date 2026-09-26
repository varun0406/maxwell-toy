import xml.etree.ElementTree as ET
tree = ET.parse('../MCMPL_20260924_MSAll.DAT')
root = tree.getroot()

for acc in root.findall('.//Account')[:10]:
    name = acc.findtext('Name')
    opbal = acc.findtext('OPBal')
    if opbal and opbal != '0.00':
        print(f"Account: {name}, OPBal: {opbal}")
        for child in acc:
            if 'bal' in child.tag.lower() or 'cr' in child.tag.lower() or 'dr' in child.tag.lower() or 'type' in child.tag.lower():
                print(f"  {child.tag}: {child.text}")
