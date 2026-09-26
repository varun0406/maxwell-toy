import sys
sys.path.append('.')
from app.database import SessionLocal
from app.models import Party
import xml.etree.ElementTree as ET
from collections import defaultdict

session = SessionLocal()
tree = ET.parse('../TR.DAT')
root = tree.getroot()

party_names_in_sales = defaultdict(int)
for sale in root.findall('.//Sales/Sale'):
    n = sale.findtext('MasterName1', '').strip()
    if n:
        party_names_in_sales[n] += 1

print(f"{'#':<3} {'Party Name':<45} {'# Sales':<10} {'In DB?'}")
print("-" * 75)
missing = []
found = []
for name, count in sorted(party_names_in_sales.items()):
    p = session.query(Party).filter(Party.name == name).first()
    if not p:
        missing.append((name, count))
    else:
        found.append((name, count))

for i, (name, count) in enumerate(missing, 1):
    print(f"{i:<3} {name:<45} {count:<10} ❌ MISSING")

print(f"\n{'─'*75}")
print(f"Total missing: {len(missing)} parties → {sum(c for _,c in missing)} sales invoices affected")
print(f"Total found:   {len(found)} parties → {sum(c for _,c in found)} sales invoices safe")
session.close()
