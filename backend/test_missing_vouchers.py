import xml.etree.ElementTree as ET

files = ['../BUSY 24-25.DAT', '../BUSY 25-26.DAT', '../BUSY26-27..DAT']

handled_tags = {'Sale', 'Receipt', 'Journal', 'SaleReturn', 'Payment', 'CrNote', 'DbNote'}

missing_vouchers = {}

for f in files:
    try:
        tree = ET.parse(f)
        root = tree.getroot()
        
        # We look at ALL tags that might have AccDetail children
        for elem in root:
            if elem.tag in handled_tags:
                continue
                
            # Check if this voucher has any Sundry Debtor inside it
            for acc_det in elem.findall('.//AccDetail'):
                grp = acc_det.findtext('tmpGroupName')
                if grp == 'Sundry Debtors':
                    if elem.tag not in missing_vouchers:
                        missing_vouchers[elem.tag] = 0
                    missing_vouchers[elem.tag] += 1
    except Exception as e:
        pass

print("Missing Vouchers affecting Sundry Debtors:")
for k, v in missing_vouchers.items():
    print(f"Tag: {k}, Occurrences: {v}")
    
