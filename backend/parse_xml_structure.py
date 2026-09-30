import xml.etree.ElementTree as ET

f = '../BUSY26-27..DAT'
tree = ET.parse(f)
root = tree.getroot()

for acc in root.findall('.//Accounts/Account'):
    name = acc.findtext('Name')
    if name and 'RAJA BHAI' in name:
        print(f"\nExample of Account {name}:")
        for sub in acc:
            if sub.text and sub.text.strip():
                print(f"  {sub.tag}: {sub.text.strip()}")
        break
