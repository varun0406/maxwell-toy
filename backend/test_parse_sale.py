import xml.etree.ElementTree as ET

tree = ET.parse("../BUSY 24-25.DAT")
root = tree.getroot()

sales = root.findall('.//Sale')
if sales:
    sale = sales[0]
    print(ET.tostring(sale, encoding='unicode')[:2000])

