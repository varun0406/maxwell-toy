import xml.etree.ElementTree as ET

file = "../busy-25-26..DAT"
root = ET.parse(file).getroot()

for acc in root.findall(".//AccountMaster"):
    name = acc.findtext("Name") or ""
    if "TARUN" in name.upper() or "DEEPAK" in name.upper():
        print(f"\n--- {name} ---")
        for child in acc:
            print(f"{child.tag}: {child.text}")
