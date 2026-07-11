import re

with open("web.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove the second occurrence of DASHBOARD_HTML and everything up to the second # --- планировщик
# Actually, since it was replaced twice, there are two DASHBOARD_HTML blocks.
# I can just find all occurrences of DASHBOARD_HTML = """ and keep only the first one.

parts = content.split('DASHBOARD_HTML = """<!doctype html>')
if len(parts) > 2:
    # Meaning it appeared at least twice
    # We want to reconstruct it but only keep the first one.
    # The block ends with `# --- планировщик`
    # Let's just find the exact block and replace it.
    
    # A safer way:
    # The duplicate block starts at DASHBOARD_HTML = ...
    # And ends at the end of custom_dashboard()
    pass

import sys
# Read lines and filter out the second definition
with open("web.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

out = []
found_dashboard = False
skip = False
for line in lines:
    if line.startswith('DASHBOARD_HTML = """<!doctype html>'):
        if found_dashboard:
            skip = True
        else:
            found_dashboard = True
    
    if skip:
        # We need to stop skipping once we hit the next `# --- планировщик`
        if line.strip() == "# --- планировщик: дневной прогон ---":
            skip = False
            out.append(line)
        elif line.strip() == "# --- планировщик":
            skip = False
            out.append(line)
    else:
        out.append(line)

with open("web.py", "w", encoding="utf-8") as f:
    f.writelines(out)
print("Fix applied")
