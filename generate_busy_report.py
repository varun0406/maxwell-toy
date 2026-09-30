import xml.etree.ElementTree as ET
from collections import defaultdict
import os

filepath = "/home/varun/Documents/maxwellMobAcc/BUSY26-27..DAT"
outpath = "/home/varun/.gemini/antigravity-ide/brain/730e3749-6b93-4613-978f-f01a99c386cc/busy_analysis.md"

tree = ET.parse(filepath)
root = tree.getroot()

# { tag: { "count": int, "attributes": set, "children": set, "parent": set } }
structure = defaultdict(lambda: {"count": 0, "attributes": set(), "children": set(), "parent": set()})

# To track interconnectivity via ID-like fields
id_fields = ['tmpCode', 'tmpVchCode', 'tmpMasterCode1', 'tmpMasterCode2', 'tmpItemCode', 'tmpAccCode', 'tmpBSCode', 'tmpPartyCode', 'tmpParentGrpCode']
field_values = defaultdict(lambda: defaultdict(set)) # { field_name: { tag: set(values) } }

def traverse(node, parent_tag=None):
    tag = node.tag
    structure[tag]["count"] += 1
    structure[tag]["attributes"].update(node.attrib.keys())
    
    if parent_tag:
        structure[tag]["parent"].add(parent_tag)
        structure[parent_tag]["children"].add(tag)
        
    for child in node:
        if child.tag in id_fields and child.text:
            field_values[child.tag][tag].add(child.text)
        traverse(child, tag)

traverse(root)

with open(outpath, "w") as f:
    f.write("# BUSY Data File (DAT) In-Depth Analysis\n\n")
    
    f.write("## 1. Overview and Root Structure\n")
    f.write("The root element is `<BusyData>` which acts as the container for all configurations, master data, and transactions.\n\n")
    
    f.write("### Main Nodes under `BusyData`\n")
    for child in sorted(structure['BusyData']['children']):
        f.write(f"- **`{child}`** ({structure[child]['count']} entries): Contains records for `{child}`.\n")
    f.write("\n")
    
    f.write("## 2. Master Data Structures\n")
    masters = ['Accounts', 'Items', 'MaterialCenters', 'BillSundries', 'Units']
    for m in masters:
        if m in structure:
            f.write(f"### {m}\n")
            f.write(f"Contains `{structure[m]['count']}` elements. Typical children are the singular elements (e.g., `{m[:-1]}`).\n")
            if m[:-1] in structure:
                singular = m[:-1]
                if m == 'BillSundries': singular = 'BillSundry'
                if singular in structure:
                    f.write(f"- **Key Attributes/Children**: {', '.join(sorted(list(structure[singular]['children'])[:15]))}...\n")
    f.write("\n")
    
    f.write("## 3. Transactions (Vouchers)\n")
    vouchers = ['Sales', 'SaleReturns', 'Purchases', 'PurchaseReturns', 'Receipts', 'Payments', 'Journals']
    for v in vouchers:
        if v in structure:
            f.write(f"### {v}\n")
            f.write(f"Contains `{structure[v]['count']}` transaction records.\n")
            singular = v[:-1]
            if v == 'Journals': singular = 'Journal'
            if singular in structure:
                f.write(f"- **Voucher Fields**: {', '.join(sorted(list(structure[singular]['children'])[:20]))}...\n")
                if 'ItemDetail' in structure[singular]['children']:
                    f.write("  - **Nested `ItemDetail`**: Represents line items (products) in the voucher.\n")
                if 'AccDetail' in structure[singular]['children']:
                    f.write("  - **Nested `AccDetail`**: Represents accounting debits/credits.\n")
                if 'BSDetail' in structure[singular]['children']:
                    f.write("  - **Nested `BSDetail`**: Represents Bill Sundry details (taxes, discounts).\n")
                if 'BillDetails' in structure[singular]['children']:
                    f.write("  - **Nested `BillDetails`**: Tracks bill-by-bill references.\n")
    f.write("\n")
    
    f.write("## 4. Interconnectivity and Relational Mappings\n")
    f.write("The BUSY XML file uses `tmpCode` and similar fields as surrogate primary/foreign keys to link entities.\n\n")
    
    for field, tag_dict in field_values.items():
        f.write(f"### `{field}`\n")
        f.write("Shared across the following tags:\n")
        for tag, vals in tag_dict.items():
            f.write(f"- **{tag}**: {len(vals)} unique values.\n")
        
        tags = list(tag_dict.keys())
        if len(tags) > 1:
            f.write(f"\n*Analysis*: The `{field}` acts as a bridge connecting `<{tags[0]}>` with `<{tags[1]}>` (and others).\n\n")
    
    f.write("## 5. Summary of Important Nestations\n")
    f.write("1. **Voucher Level (e.g. `<Sale>`)**\n")
    f.write("   - `tmpVchCode`: Unique Voucher ID\n")
    f.write("   - `<ItemDetail>`: 1-to-many relationship for inventory items sold.\n")
    f.write("   - `<AccDetail>`: 1-to-many relationship for ledger posting (Party Dr, Sales Cr).\n")
    f.write("   - `<BSDetail>`: 1-to-many relationship for taxes/charges applied at the bottom of the invoice.\n")
    f.write("   - `<BillingDetails>` / `<BillDetails>`: Tracking for aging and payments against this specific invoice.\n\n")
    
    f.write("2. **Master Level (e.g. `<Account>`)**\n")
    f.write("   - `<Address>`: Contact information nesting.\n")
    f.write("   - `tmpCode`: Unique Account ID, referenced as `tmpPartyCode` in Sales, or `tmpAccCode` in `<AccDetail>`.\n\n")

    f.write("## 6. Full Reference of Tags (A-Z)\n")
    f.write("| Tag | Count | Parent(s) | Key Children |\n")
    f.write("|---|---|---|---|\n")
    for tag, info in sorted(structure.items()):
        parents = ', '.join(sorted(info['parent']))[:50]
        children = ', '.join(sorted(info['children']))[:100]
        f.write(f"| `{tag}` | {info['count']} | {parents} | {children}... |\n")

print("Artifact written successfully.")
