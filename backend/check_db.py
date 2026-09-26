import xml.etree.ElementTree as ET
tree = ET.parse('../TR.DAT')
root = tree.getroot()

print("--- SALE ---")
for acc in root.find('.//Sales/Sale').findall('.//AccEntries/AccDetail'):
    print(acc.findtext('AccountName'), acc.findtext('AmountType'), acc.findtext('AmtMainCur'), acc.findtext('tmpGroupName'))

print("--- RCPT ---")
for acc in root.find('.//Rcpts/Receipt').findall('.//AccEntries/AccDetail'):
    print(acc.findtext('AccountName'), acc.findtext('AmountType'), acc.findtext('AmtMainCur'), acc.findtext('tmpGroupName'))
    
print("--- JRNL ---")
for acc in root.find('.//Jrnls/Journal').findall('.//AccEntries/AccDetail'):
    print(acc.findtext('AccountName'), acc.findtext('AmountType'), acc.findtext('AmtMainCur'), acc.findtext('tmpGroupName'))
