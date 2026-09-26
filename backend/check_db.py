import xml.etree.ElementTree as ET
from collections import Counter

tree = ET.parse('../TR.DAT')
root = tree.getroot()

print("Top Level Nodes:")
for child in root:
    print(child.tag)

print("\nVchTypes found in file:")
vch_types = Counter()
for v in root.findall('.//VchType'):
    vch_types[v.text] += 1
for k, v in vch_types.items():
    print(f"VchType {k}: {v}")
