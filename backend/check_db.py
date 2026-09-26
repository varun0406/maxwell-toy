import sys
sys.path.append('.')
from app.database import SessionLocal
from app.models import Party
import xml.etree.ElementTree as ET
from collections import defaultdict

session = SessionLocal()

tree = ET.parse('../BUSY 25-26.DAT')
root = tree.getroot()

# The 28 missing party names from sales
missing_names = [
    "RAJU BHAI (KHOKHRA)", "MAHADEV JIGNESHBHAI (BHAVNAGAR)", "RAJA BHAI(SURAT)",
    "DEEPAKBHAI BHAVNAGAR", "ASHAPURA TRADERS ( SURAT )", "GURUNANAK GARMENT'S",
    "DILIPBHAI ( SURAT )", "MANIBHADHRA ENTERPRISE(SAFAL-04)", "RAJESH READYMADE STORES PANCHKUVA",
    "KAPILBHAI ( RAJLAXMI)", "AKSHAR CREATION BHAVNAGER", "RAHULBHAI (BHAVNAGAR)",
    "JOLLY BHAI ( SURAT )", "BHOLESHWAR REDYMADE", "SURAJ GARMENTS",
    "BHOLE GARMENTS( BHAVNAGAR )", "OM APPARELS(MATIX)", "OM CREATION (ANMOL)",
    "WAHEGURU APPARELS ( HARSH KORANI )", "ASHAPURA APPARELS( RAJ LAXMI)", "VINAY TRADER'S",
    "SHREE JI ENTERPRISE", "H & H GARMENT", "MAHADEV FASHION BHAVNAGAR",
    "JAINAM APPRAELS (K -08)", "SATISHBHAI REVDI BAZAR", "DILIP ENTERPRISE ( JUNAGADH )",
    "KRISHNA CREATION ( L V MKT )"
]

# Build set of account names in BUSY 25-26.DAT Accounts section
accounts_in_25_26 = {
    acc.findtext('Name', '').strip()
    for acc in root.findall('.//Accounts/Account')
    if acc.findtext('ParentGroup', '') == 'Sundry Debtors'
}

party_sales = defaultdict(int)
for sale in root.findall('.//Sales/Sale'):
    n = sale.findtext('MasterName1', '').strip()
    if n in missing_names:
        party_sales[n] += 1

print(f"{'#':<3} {'Party Name':<48} {'Sales':<7} {'In 25-26 Accounts?'}")
print("-" * 85)
in_accounts = 0
not_in_accounts = 0
for i, name in enumerate(sorted(missing_names, key=lambda n: -party_sales.get(n, 0)), 1):
    in_acc = "✅ YES" if name in accounts_in_25_26 else "❌ NO (auto-create)"
    if name in accounts_in_25_26:
        in_accounts += 1
    else:
        not_in_accounts += 1
    print(f"{i:<3} {name:<48} {party_sales.get(name,0):<7} {in_acc}")

print(f"\nIn BUSY 25-26.DAT Accounts: {in_accounts}")
print(f"Auto-created on import    : {not_in_accounts}")
print(f"Total accounts in 25-26 Accounts section: {len(accounts_in_25_26)}")
session.close()
