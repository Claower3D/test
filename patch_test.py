import web
with web.app.test_client() as c:
    rv = c.get('/dashboard')
    html = rv.data.decode('utf-8')
    print("Has {bot_runs}:", "{bot_runs}" in html)
    print("Has pieChart:", "pieChart" in html)
