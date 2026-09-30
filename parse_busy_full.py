import xml.etree.ElementTree as ET
from collections import defaultdict
import os

filepath = "/home/varun/Documents/maxwellMobAcc/BUSY26-27..DAT"
tree = ET.parse(filepath)
root = tree.getroot()

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

with open("busy_structure_analysis.txt", "w") as f:
    f.write("XML Structure Analysis for BUSY26-27..DAT\n")
    f.write("========================================\n\n")
    
    # Sort tags for logical grouping: Top level first, then by name
    for tag, info in sorted(structure.items()):
        f.write(f"Tag: <{tag}> (Count: {info['count']})\n")
        f.write(f"  Parents: {', '.join(sorted(info['parent'])) if info['parent'] else 'ROOT'}\n")
        f.write(f"  Children: {', '.join(sorted(info['children'])) if info['children'] else 'None'}\n")
        f.write(f"  Attributes: {', '.join(sorted(info['attributes'])) if info['attributes'] else 'None'}\n")
        f.write("\n")

