import re
with open("../busy-25-26..DAT", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()
    
idx = content.find("25-26-756")
start = content.rfind("<Sale>", 0, idx)
end = content.find("</Sale>", idx)
print(content[start:end+7])
