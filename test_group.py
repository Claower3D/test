import re
import os

def parse_links_for_grouping():
    groups = {}
    current_batch = "Прочие"
    
    if os.path.exists("links.txt"):
        with open("links.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("http"):
                    groups.setdefault(current_batch, []).append(line)
                elif "," in line or line.isdigit():
                    ids = [x.strip() for x in line.replace(" (снято)", "").split(",") if x.strip().isdigit()]
                    if ids:
                        groups.setdefault(current_batch, []).extend(ids)
                elif "ПАЧКА" in line.upper() or "📦" in line or "🎯" in line or "MIX" in line.upper() or "ТЕСТ" in line.upper():
                    current_batch = line.replace("📦", "").replace("🎯", "").replace("───────────────────────────────────────────", "").strip()
                    current_batch = current_batch.split("—")[0].strip()
    return groups

print(parse_links_for_grouping())
