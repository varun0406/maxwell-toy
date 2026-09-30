import xml.etree.ElementTree as ET
from collections import defaultdict
import os

filepath = "/home/varun/Documents/maxwellMobAcc/BUSY26-27..DAT"
if not os.path.exists(filepath):
    print("File not found.")
    exit(1)

try:
    tree = ET.parse(filepath)
    root = tree.getroot()
except Exception as e:
    print(f"Error parsing XML: {e}")
    # try reading as raw text to see first few lines
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        print("First 1000 chars of file:")
        print(f.read(1000))
    exit(1)

# Dictionary to hold the structure
# { tag: { "count": int, "attributes": set, "children": set, "parent": set } }
structure = defaultdict(lambda: {"count": 0, "attributes": set(), "children": set(), "parent": set()})

def traverse(node, parent_tag=None):
    tag = node.tag
    structure[tag]["count"] += 1
    structure[tag]["attributes"].update(node.attrib.keys())
    
    if parent_tag:
        structure[tag]["parent"].add(parent_tag)
        structure[parent_tag]["children"].add(tag)
        
    for child in node:
        traverse(child, tag)

traverse(root)

print("XML Structure Analysis:")
for tag, info in sorted(structure.items()):
    print(f"\nTag: <{tag}> (Count: {info['count']})")
    print(f"  Parents: {', '.join(info['parent']) if info['parent'] else 'None'}")
    print(f"  Children: {', '.join(info['children']) if info['children'] else 'None'}")
    print(f"  Attributes: {', '.join(info['attributes']) if info['attributes'] else 'None'}")
