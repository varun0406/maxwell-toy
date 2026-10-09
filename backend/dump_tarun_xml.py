import xml.etree.ElementTree as ET

files = ["../busy-24-25a.DAT", "../busy-25-26..DAT", "../busy 26-27....DAT"]

for file in files:
    try:
        root = ET.parse(file).getroot()
        for v in root.iter():
            if v.tag in ["Sale", "SaleReturn", "Receipt", "Payment", "Journal", "DebitNote", "CreditNote"]:
                found = False
                for acc in v.findall(".//AccDetail"):
                    name = acc.findtext("AccountName") or acc.findtext("MasterName1") or acc.findtext("MasterName2") or ""
                    if "TARUN" in name.upper():
                        found = True
                        break
                
                if found:
                    print(f"\n--- {v.tag} VchNo: {v.findtext('VchNo')} Date: {v.findtext('Date')} ---")
                    for acc in v.findall(".//AccDetail"):
                        name = acc.findtext("AccountName") or acc.findtext("MasterName1") or acc.findtext("MasterName2") or ""
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
