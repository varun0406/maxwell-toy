import xml.etree.ElementTree as ET

f = '../BUSY26-27..DAT'
tree = ET.parse(f)
root = tree.getroot()

for acc in root.findall('.//AccountMaster'):
    name = acc.findtext('Name')
    if name and 'RAJA BHAI' in name:
        print("Found RAJA BHAI Master:")
        for child in acc:
            if child.text and child.text.strip():
                print(f"  {child.tag}: {child.text.strip()}")
        break
