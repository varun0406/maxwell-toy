import xml.etree.ElementTree as ET

files = ["../busy-24-25a.DAT", "../busy-25-26..DAT", "../busy 26-27....DAT"]

for file in files:
    try:
        root = ET.parse(file).getroot()
        
        # Build account map
        account_map = {}
        for acc in root.findall('.//AccountMaster'):
            code = acc.findtext('MasterCode') or acc.findtext('tmpMasterCode1')
            name = acc.findtext('Name')
            if code and name:
                account_map[code.strip()] = name.strip()
                
        def get_party_name(element):
            name1 = element.findtext('MasterName1')
            if name1: return name1
            name2 = element.findtext('AccountName')
            if name2: return name2
            code1 = element.findtext('MasterCode1')
            if code1 and code1.strip() in account_map: return account_map[code1.strip()]
            tcode1 = element.findtext('tmpMasterCode1')
            if tcode1 and tcode1.strip() in account_map: return account_map[tcode1.strip()]
            tcode = element.findtext('tmpAccCode')
            if tcode and tcode.strip() in account_map: return account_map[tcode.strip()]
            return ""

        for v in root.iter():
            if v.tag in ["Sale", "SaleReturn", "Receipt", "Payment", "Journal", "DebitNote", "CreditNote"]:
                found = False
                for acc in v.findall(".//AccDetail"):
                    name = get_party_name(acc)
                    if "TARUN" in name.upper():
                        found = True
                        break
                
                if found:
                    print(f"\n--- {v.tag} VchNo: {v.findtext('VchNo')} Date: {v.findtext('Date')} ---")
                    for acc in v.findall(".//AccDetail"):
                        name = get_party_name(acc)
                        if "TARUN" in name.upper():
                            print(f"  Amt: {acc.findtext('AmtMainCur')} Type: {acc.findtext('AmountType')}")
                            br = acc.find("BillRefs")
                            if br is not None and len(br.findall("BillDetails")) > 0:
                                for b in br.findall("BillDetails"):
                                    print(f"    RefNo: {b.findtext('RefNo')} Value: {b.findtext('Value1')}")
                            else:
                                print("    No BillRefs")
    except Exception as e:
        pass
