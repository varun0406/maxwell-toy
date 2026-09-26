import sys
sys.path.append('.')
from app.database import SessionLocal
from app.models import Party, Invoice
import xml.etree.ElementTree as ET
from collections import defaultdict

session = SessionLocal()

# After the fresh reset + import, check which of the 28 are NOW in DB
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

print("--- Are the 28 missing parties in DB RIGHT NOW? ---")
in_db = []
not_in_db = []
for name in missing_names:
    p = session.query(Party).filter(Party.name == name).first()
    if p:
        in_db.append((name, p.id))
    else:
        not_in_db.append(name)

print(f"Found in DB  : {len(in_db)}")
print(f"NOT in DB    : {len(not_in_db)}")
for n in not_in_db:
    print(f"  ❌ {n}")

# Now check invoices for the ones that ARE in DB
print("\n--- Invoices imported for parties that ARE in DB ---")
for name, pid in in_db[:5]:
    inv_count = session.query(Invoice).filter(Invoice.party_id == pid).count()
    print(f"  {name} -> {inv_count} invoices")

# Total sales vs total DB invoices
tree = ET.parse('../BUSY 25-26.DAT')
root = tree.getroot()
total_sales_xml = len(root.findall('.//Sales/Sale'))
total_inv_db = session.query(Invoice).count()
print(f"\nTotal Sales in XML  : {total_sales_xml}")
print(f"Total Invoices in DB: {total_inv_db}")
session.close()
