import xml.etree.ElementTree as ET
from collections import defaultdict
import os

filepath = "/home/varun/Documents/maxwellMobAcc/BUSY.DAT"
outpath = "/home/varun/.gemini/antigravity-ide/brain/730e3749-6b93-4613-978f-f01a99c386cc/busy_masters_analysis.md"

if not os.path.exists(filepath):
    print("File not found.")
    exit(1)

try:
    tree = ET.parse(filepath)
    root = tree.getroot()
except Exception as e:
    print(f"Error parsing XML: {e}")
    exit(1)

masters_tags = [
    'Accounts', 'Items', 'MaterialCenters', 'BillSundries', 'Units', 
    'Brokers', 'CostCenters', 'SaleTypes', 'PurchaseTypes'
]

# We want to understand what tags exist under each singular master (e.g., inside <Account> inside <Accounts>)
master_structure = defaultdict(lambda: {"count": 0, "children_counts": defaultdict(int), "attributes": set()})

# Also we want a sample of the first element to show what it looks like
samples = {}

for master_group_tag in masters_tags:
    group_node = root.find(master_group_tag)
    if group_node is not None:
        # Assuming the singular tag is usually the group name minus 's' (e.g. Accounts -> Account)
        # or we just iterate all children of the group node.
        for child in group_node:
            tag = child.tag
            master_structure[tag]["count"] += 1
            master_structure[tag]["attributes"].update(child.attrib.keys())
            
            if tag not in samples:
                # Capture the first one as a sample
                sample_dict = {}
                for field in child:
                    sample_dict[field.tag] = field.text
                samples[tag] = sample_dict
                
            for field in child:
                master_structure[tag]["children_counts"][field.tag] += 1

with open(outpath, "w") as f:
    f.write("# BUSY.DAT Masters Analysis\n\n")
    f.write("This report provides an in-depth analysis of the Master data structures (Accounts, Items, Units, Bill Sundries, etc.) found in `BUSY.DAT`.\n\n")
    
    if not master_structure:
        f.write("No master records found in the file.\n")
    else:
        for tag, info in sorted(master_structure.items()):
            f.write(f"## Master: `<{tag}>`\n")
            f.write(f"- **Total Records**: {info['count']}\n")
            if info['attributes']:
                f.write(f"- **Attributes**: {', '.join(info['attributes'])}\n")
            f.write("\n### Data Fields (Children)\n")
            f.write("| Field Name | Occurrence (How many records have it) | Example Value (from first record) |\n")
            f.write("|---|---|---|\n")
            
            # Sort fields by occurrence (most common first) then alphabetically
            sorted_fields = sorted(info["children_counts"].items(), key=lambda x: (-x[1], x[0]))
            
            for field, count in sorted_fields:
                example_val = samples[tag].get(field, "")
                if example_val is None:
                    example_val = "*(empty)*"
                # truncate long examples
                if len(example_val) > 40:
                    example_val = example_val[:37] + "..."
                f.write(f"| `{field}` | {count} / {info['count']} | `{example_val}` |\n")
            
            f.write("\n---\n\n")

print("Masters artifact written successfully.")
