import xml.etree.ElementTree as ET
tree = ET.parse('../TR.DAT')
root = tree.getroot()
print("--- SEARCHING FOR NARRATION ---")
for sale in root.findall('.//Sales/Sale')[:10]:
    for acc in sale.findall('.//AccEntries/AccDetail'):
        short = acc.findtext('ShortNar')
        if short:
            print("Sale ShortNar:", short)
            
for jrnl in root.findall('.//Jrnls/Journal')[:10]:
    for acc in jrnl.findall('.//AccEntries/AccDetail'):
        short = acc.findtext('ShortNar')
        if short:
            print("Jrnl ShortNar:", short)

print("--- JRNL AccEntries ---")
jrnl = root.find('.//Jrnls/Journal')
if jrnl is not None:
    for acc in jrnl.findall('.//AccEntries/AccDetail'):
        print(acc.findtext('AccountName'), acc.findtext('AmtMainCur'), acc.findtext('AmountType'), acc.findtext('ShortNar'))

print("--- BillSundries ---")
for sale in root.findall('.//Sales/Sale'):
    bs = sale.find('.//BillSundries')
    if bs is not None and list(bs):
        for bsd in bs.findall('.//BillSundryDetail'):
            print("BillSundry:", bsd.findtext('BillSundryName'), bsd.findtext('SurchargeName'), bsd.findtext('AmtMainCur'), bsd.findtext('tmpAmount'))
        break
