import xml.etree.ElementTree as ET
from collections import defaultdict
import os

def collect_paths(node, current_path, schema_dict):
    """Recursively collect all tag paths and record how many times they appear."""
    for child in node:
        path = f"{current_path}/{child.tag}"
        # If the tag has no children, it's a leaf node. We count it.
        if not list(child):
            schema_dict[path] += 1
        else:
            # If it has children, we recurse
            collect_paths(child, path, schema_dict)

def analyze_file(file_path):
    print(f"Parsing {file_path}...")
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = "<root>" + f.read() + "</root>"
        root = ET.fromstring(content)

    # Categories to analyze
    categories = {
        'Sales': './/Sales/Sale',
        'SaleReturns': './/SlRts/SaleReturn',
        'Receipts': './/Rcpts/Receipt',
        'Journals': './/Jrnls/Journal'
    }

    report = []
    report.append("# TR.DAT Schema Analysis Report\n")

    for cat_name, xpath in categories.items():
        schema_dict = defaultdict(int)
        nodes = root.findall(xpath)
        report.append(f"## {cat_name} (Total Records: {len(nodes)})\n")
        
        for node in nodes:
            collect_paths(node, node.tag, schema_dict)
            
        # Sort and format the paths
        if schema_dict:
            report.append("```text")
            for path in sorted(schema_dict.keys()):
                report.append(f"{path} (Occurrences: {schema_dict[path]})")
            report.append("```\n")
        else:
            report.append("*No records found*\n")

    # Save to artifacts directory
    output_path = "/home/varun/.gemini/antigravity-ide/brain/5663cc6a-620d-49e7-b532-92c2a6a4764b/scratch/TR_schema_analysis.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write("\n".join(report))
        
    print(f"Analysis saved to {output_path}")

if __name__ == "__main__":
    analyze_file("../TR.DAT")
