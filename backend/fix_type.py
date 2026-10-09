with open("compare_onaccount.py", "r") as f:
    code = f.read()
code = code.replace("our_val = row[1] if row else Decimal('0')", "our_val = Decimal(str(row[1])) if row and row[1] is not None else Decimal('0')")
with open("compare_onaccount.py", "w") as f:
    f.write(code)
