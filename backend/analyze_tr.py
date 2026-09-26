import xml.etree.ElementTree as ET

tree = ET.parse('../TR.DAT')
root = tree.getroot()

print("--- FULL SLRT BILLREFS ---")
for slrt in root.findall('.//SlRts/SaleReturn'):
    for acc in slrt.findall('.//AccEntries/AccDetail'):
        bill_refs = acc.find('BillRefs')
        if bill_refs is not None and list(bill_refs):
            print(f"\nSaleReturn for {acc.findtext('AccountName')}:")
            for bd in bill_refs.findall('BillDetails'):
                print(f"  RefNo: {bd.findtext('RefNo')}, Value1: {bd.findtext('Value1')}")
                
print("\n--- FULL JOURNAL BILLREFS ---")
for jrnl in root.findall('.//Jrnls/Journal'):
    for acc in jrnl.findall('.//AccEntries/AccDetail'):
        bill_refs = acc.find('BillRefs')
        if bill_refs is not None and list(bill_refs):
            print(f"\nJournal for {acc.findtext('AccountName')}:")
            for bd in bill_refs.findall('BillDetails'):
                print(f"  RefNo: {bd.findtext('RefNo')}, Value1: {bd.findtext('Value1')}")
