import xml.etree.ElementTree as ET
import glob

files = ['../busy(26-27)master.DAT', '../busy(26-27).DAT']

for f in files:
    try:
        tree = ET.parse(f)
        root = tree.getroot()
        for acc in root.findall('.//Accounts/Account'):
            name = acc.findtext('Name')
            if name and 'DEEPLAXMI' in name:
                print(f"--- File: {f} ---")
                for child in acc:
                    if 'bal' in child.tag.lower() or 'close' in child.tag.lower():
                        print(f"  {child.tag}: {child.text}")
    except Exception as e:
        print(f"Error parsing {f}: {e}")
