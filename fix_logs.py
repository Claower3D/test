import codecs

content = codecs.open('web.py', 'r', 'utf-8').read()

import re

# We want to remove the garbage code from inside logs_page().
# The garbage starts at "groups_data = load_whatsapp_groups()"
# and ends right before "<script>"

start_marker = "    groups_data = load_whatsapp_groups()"
end_marker = '    <script>'

if start_marker in content and end_marker in content:
    # Find the last occurrence of logs_page to ensure we are in the right place
    idx = content.find("def logs_page():")
    if idx != -1:
        start_idx = content.find(start_marker, idx)
        end_idx = content.find(end_marker, start_idx)
        if start_idx != -1 and end_idx != -1:
            content = content[:start_idx] + content[end_idx:]
            with codecs.open('web.py', 'w', 'utf-8') as f:
                f.write(content)
            print("Fixed logs_page() successfully.")
        else:
            print("Markers not found after logs_page.")
else:
    print("Markers not found in content.")
