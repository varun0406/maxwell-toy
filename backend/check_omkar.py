import xml.etree.ElementTree as ET

tree = ET.parse('BUSY26-27..DAT')
root = tree.getroot()

for rcpt in root.findall('.//Rcpts/Receipt'):
    for acc in rcpt.findall('.//AccEntries/AccDetail'):
        name = acc.findtext('AccountName', '').strip()
        amt = acc.findtext('AmtMainCur', '0')
        if name == "OMKAR GARMENT'S (JIGABHAI)" and amt == "100000":
            print("Receipt:")
            print("OriginalID:", rcpt.findtext('OriginalID'))
            print("tmpVchCode:", rcpt.findtext('tmpVchCode'))
            print("---")
