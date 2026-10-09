import xml.etree.ElementTree as ET

files = ["../busy-24-25a.DAT", "../busy-25-26..DAT", "../busy 26-27....DAT"]
targets = ["25-26-756", "25-26-1177", "25-26-1281"]

for file in files:
    try:
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            for target in targets:
                if target in content:
                    print(f"Target '{target}' found in {file}!")
                    
        # Also parse XML to find the exact tags
        root = ET.parse(file).getroot()
        for elem in root.iter():
            if elem.text and any(t in elem.text for t in targets):
                print(f"Found in tag <{elem.tag}>: {elem.text}")
    except Exception as e:
        pass
