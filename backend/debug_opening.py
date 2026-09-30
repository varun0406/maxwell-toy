import xml.etree.ElementTree as ET
party_name = 'RAJA BHAI(SURAT)'
files = ['../BUSY 24-25.DAT', '../BUSY 25-26.DAT', '../BUSY26-27..DAT']

for f in files:
    tree = ET.parse(f)
    root = tree.getroot()
    for acc in root.findall('.//Accounts/Account'):
        name = acc.findtext('Name')
        if name and 'RAJA BHAI' in name:
            opbal = acc.findtext('OPBal')
            pybal = acc.findtext('PYBal')
            print(f"{f}: OPBal={opbal}, PYBal={pybal}")
