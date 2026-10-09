import re
with open("../busy-25-26..DAT", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()
    
# Find TARUN in AccDetail
idx = content.find("TARUN")
while idx != -1:
    start = content.rfind("<Receipt>", 0, idx)
    end = content.find("</Receipt>", idx)
    if start != -1 and end != -1 and "73000" in content[start:end]:
        print(content[start:end+10])
        break
    idx = content.find("TARUN", idx+1)
