import xml.etree.ElementTree as ET
files = ["../busy-25-26..DAT", "../busy 26-27....DAT"]
for file in files:
    try:
        root = ET.parse(file).getroot()
        for v in root.findall(".//Receipt"):
            for acc in v.findall(".//AccDetail"):
                name = acc.findtext('MasterName1') or ""
                if "TARUN" in name.upper():
                    print(f"Receipt {v.findtext('VchNo')} on {v.findtext('Date')}")
                    br = acc.find("BillRefs")
                    if br is not None:
                        for b in br.findall("BillDetails"):
                            print(f"  RefNo: {b.findtext('RefNo')} Value: {b.findtext('Value1')}")
                    else:
                        print("  No BillRefs")
    except Exception as e:
        print(f"Error {file}: {e}")
