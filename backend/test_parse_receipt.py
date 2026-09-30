import xml.etree.ElementTree as ET

tree = ET.parse("../BUSY 24-25.DAT")
root = tree.getroot()

receipts = root.findall('.//Receipt')
if receipts:
    rcpt = receipts[0]
    print(ET.tostring(rcpt, encoding='unicode')[:2000])

