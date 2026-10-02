import xml.etree.ElementTree as ET

for file in ["/home/varun/Documents/maxwellMobAcc/busy-25-26..DAT", "/home/varun/Documents/maxwellMobAcc/busy-24-25a.DAT"]:
    try:
        tree = ET.parse(file)
        root = tree.getroot()
        for rcpt in root.findall('.//Receipt'):
            vch_no = rcpt.findtext('VchNo')
            for acc in rcpt.findall('.//AccDetail'):
                name = acc.findtext('MasterName1') or ''
                if 'DEEPAKBHAI' in name.upper() and 'BHAVNAGAR' in name.upper():
                    print(f"File: {file} - Receipt: {vch_no}")
                    print(ET.tostring(acc, encoding='unicode'))
                    print("="*40)
    except Exception as e:
        print(e)
