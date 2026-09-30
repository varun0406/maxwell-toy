import xml.etree.ElementTree as ET

files = ['../BUSY 24-25.DAT', '../BUSY 25-26.DAT', '../BUSY26-27..DAT']

summary = {}

for f in files:
    try:
        tree = ET.parse(f)
        root = tree.getroot()
        
        for elem in root:
            if not isinstance(elem.tag, str): continue
                
            has_debtor = False
            for acc_det in elem.findall('.//AccDetail'):
                if acc_det.findtext('tmpGroupName') == 'Sundry Debtors':
                    has_debtor = True
                    break
            
            if has_debtor:
                tag_name = elem.tag
                if tag_name not in summary:
                    summary[tag_name] = 0
                summary[tag_name] += 1
    except Exception as e:
        pass

for k, v in summary.items():
    print(f"{k}: {v} vouchers")
