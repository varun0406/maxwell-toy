import xml.etree.ElementTree as ET
import glob

files = ['../BUSY 24-25.DAT', '../BUSY 25-26.DAT', '../BUSY26-27..DAT']

for f in files:
    tree = ET.parse(f)
    root = tree.getroot()
    for acc in root.findall('.//Accounts/Account'):
        name = acc.findtext('Name')
        if name and 'RAJA BHAI' in name:
            print(f"--- File: {f} ---")
            for child in acc:
                if 'Bal' in child.tag or 'bal' in child.tag.lower() or 'close' in child.tag.lower():
                    print(f"  {child.tag}: {child.text}")
