import xml.etree.ElementTree as ET
files = ["../busy-25-26..DAT", "../busy 26-27....DAT"]
for file in files:
    try:
        root = ET.parse(file).getroot()
        for v in root.findall(".//Journal"):
            for acc in v.findall(".//AccDetail"):
                name = acc.findtext("AccountName") or acc.findtext("MasterName1") or ""
                if "TARUN" in name.upper():
                    print("Journal", v.findtext("VchNo"), v.findtext("Date"), acc.findtext("AmtMainCur"))
                    br = acc.find("BillRefs")
                    if br is not None and len(br.findall("BillDetails")) > 0:
                        for b in br.findall("BillDetails"):
                            print(f"  RefNo: {b.findtext('RefNo')} Value: {b.findtext('Value1')}")
                    else:
                        print("  No BillRefs")
    except Exception as e:
        pass
