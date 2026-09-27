import xml.etree.ElementTree as ET

files = ['BUSY 24-25.DAT', 'BUSY 25-26.DAT', 'BUSY26-27..DAT']
for file in files:
    tree = ET.parse(file)
    root = tree.getroot()
    multi = 0
    for rcpt in root.findall('.//Rcpts/Receipt'):
        debtors = 0
        for acc in rcpt.findall('.//AccEntries/AccDetail'):
            if acc.findtext('tmpGroupName', '') == 'Sundry Debtors':
                debtors += 1
        if debtors > 1:
            multi += 1
    print(f"{file} has {multi} receipts with multiple debtors")
