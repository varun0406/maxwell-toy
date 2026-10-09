import xml.etree.ElementTree as ET
root = ET.parse("../Masters.DAT").getroot()
for acc in root.findall(".//AccountMaster"):
    name = acc.findtext("Name") or ""
    if "DEEPAK" in name.upper() or "TARUN" in name.upper():
        print(f"Party: {name}")
        print(f"  OpBal: {acc.findtext('OpBal')} OpBalType: {acc.findtext('OpBalType')}")
