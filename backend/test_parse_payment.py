import xml.etree.ElementTree as ET
try:
    tree = ET.parse('../BUSY 24-25.DAT')
    root = tree.getroot()
    p = root.find('.//Payment')
    if p is not None:
        print(ET.tostring(p, encoding='unicode'))
except Exception as e:
    print(e)
