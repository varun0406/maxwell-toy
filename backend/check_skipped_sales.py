import xml.etree.ElementTree as ET

tree = ET.parse('BUSY 24-25.DAT')
root = tree.getroot()

missing_party = 0
dup_inv = 0
seen = set()

for sale in root.findall('.//Sales/Sale'):
    vch_no = sale.findtext('VchNo', '').strip()
    party_name = sale.findtext('MasterName1', '').strip()
    
    if not party_name:
        missing_party += 1
    elif vch_no in seen:
        dup_inv += 1
    else:
        seen.add(vch_no)
        
print(f"BUSY 24-25.DAT - Missing Party: {missing_party}, Duplicate VchNo: {dup_inv}")
