import xml.etree.ElementTree as ET

f = '../busy(26-27).DAT'
tree = ET.parse(f)
root = tree.getroot()
for acc_det in root.findall('.//AccDetail'):
    name = ' '.join((acc_det.findtext('AccountName') or '').split())
    if name == 'RAJA BHAI(SURAT)':
        print(f"Found 26-27 transaction for RAJA BHAI: amt_type={acc_det.findtext('AmountType')}, amt={acc_det.findtext('AmtMainCur') or acc_det.findtext('Amount')}")
