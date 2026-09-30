import xml.etree.ElementTree as ET

tree = ET.parse("../BUSY 24-25.DAT")
root = tree.getroot()

sr = root.find('.//SaleReturn')
if sr is not None:
    print("SaleReturn:")
    print(ET.tostring(sr, encoding='unicode')[:1000])

jr = root.find('.//Journal')
if jr is not None:
    print("\nJournal:")
    print(ET.tostring(jr, encoding='unicode')[:1000])
