import requests, re
resp = requests.get('https://www.olx.kz/list/q-397364579/', headers={'User-Agent': 'Mozilla/5.0'})
links = set(re.findall(r'href="([^"]*)"', resp.text))
found = False
for l in links:
    if 'obyavlenie' in l:
        print('Found:', l)
        found = True
if not found:
    print('No obyavlenie links found!')
    print('Excerpt of links:', list(links)[:10])
