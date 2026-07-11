import codecs

content = codecs.open('web.py', 'r', 'utf-8').read()

endpoints = """
@app.post("/whatsapp/upload_csv")
def whatsapp_upload_csv():
    import csv
    if 'csv_file' not in request.files:
        return redirect("/whatsapp")
        
    file = request.files['csv_file']
    if file.filename == '':
        return redirect("/whatsapp")
        
    if file:
        content_bytes = file.read()
        try:
            content_str = content_bytes.decode('utf-8')
        except:
            content_str = content_bytes.decode('cp1251', errors='replace')
            
        lines = content_str.splitlines()
        
        delimiter = ','
        if lines and ';' in lines[0] and lines[0].count(';') > lines[0].count(','):
            delimiter = ';'
            
        reader = csv.reader(lines, delimiter=delimiter)
        groups = []
        for i, row in enumerate(reader):
            if i == 0 or len(row) < 3:
                continue 
            
            name = row[1].strip() if len(row) > 1 else ""
            url = row[2].strip() if len(row) > 2 else ""
            if not url.startswith("http"):
                continue
                
            groups.append({
                "id": i,
                "name": name,
                "url": url,
                "platform": row[3] if len(row) > 3 else "WhatsApp",
                "status": "waiting",
                "reason": ""
            })
            
        save_whatsapp_groups(groups)
        
    return redirect("/whatsapp")

@app.get("/whatsapp/clear_csv")
def whatsapp_clear_csv():
    save_whatsapp_groups([])
    return redirect("/whatsapp")

"""

if "def whatsapp_upload_csv():" not in content:
    content = content.replace("@app.post(\"/whatsapp/save\")", endpoints + "@app.post(\"/whatsapp/save\")")
    with codecs.open('web.py', 'w', 'utf-8') as f:
        f.write(content)
