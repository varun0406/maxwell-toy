import xml.etree.ElementTree as ET
import hashlib

def source_identity(element, voucher_type, file_path):
    payload = ET.tostring(element, encoding="utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:24]
    return f"BUSY:{file_path}:{voucher_type}:{digest}"

tree = ET.parse("../busy-25-26..DAT")
for rcpt in tree.getroot().findall(".//Receipt"):
    if source_identity(rcpt, "Receipt", "busy-25-26..DAT") == "BUSY:busy-25-26..DAT:Receipt:35ec86a39b92c4849185f0c1":
        print(ET.tostring(rcpt, encoding="unicode"))
        break
