import re

text = """
Country	IP	Port	Protocols	Anonymity	Last Checked
Kazakhstan	
89.40.233.13
1080	
SOCKS5
Elite
2026-07-02 18:10 UTC
Kazakhstan	
93.185.68.82
8080	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
194.110.55.211
3130	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
82.115.60.51
80	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
199.189.249.175
8080	
SOCKS5
Elite
2026-07-02 18:10 UTC
Kazakhstan	
176.12.74.0
3128	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
91.229.151.118
8080	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
89.169.37.254
8080	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
93.170.73.0
8081	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
176.12.74.0
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
199.189.255.230
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
2.78.60.10
3129	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
82.200.236.130
3128	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
91.244.106.26
1090	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
80.90.183.221
3128	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
92.46.70.174
1080	
SOCKS5
Elite
2026-07-02 18:10 UTC
Kazakhstan	
199.189.255.230
8080	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
45.136.59.143
1080	
SOCKS5
Elite
2026-07-02 18:10 UTC
Kazakhstan	
89.169.37.254
1080	
SOCKS4
Elite
2026-07-02 18:10 UTC
Kazakhstan	
46.8.31.104
1080	
SOCKS5
Elite
2026-07-02 18:10 UTC
Country	IP	Port	Protocols	Anonymity	Last Checked
Kazakhstan	
37.221.202.84
33333	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
199.189.255.215
1080	
SOCKS5
Elite
2026-07-02 18:10 UTC
Kazakhstan	
194.58.42.190
3128	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
94.131.230.23
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
45.10.40.218
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
72.56.3.17
1080	
SOCKS5
Elite
2026-07-02 18:10 UTC
Kazakhstan	
89.218.175.84
8080	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
213.148.6.12
7777	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
109.248.236.150
60606	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
176.12.72.62
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
80.90.183.221
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
195.133.8.226
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
213.148.9.209
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
91.185.20.162
8080	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
176.12.72.62
3128	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
199.189.255.22
8888	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
46.8.252.19
8123	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
90.156.252.74
8888	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
176.12.73.250
3128	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
199.189.249.175
80	
HTTP
Elite
2026-07-02 18:10 UTC
« 1
‹ 1
2
› 3

Country	IP	Port	Protocols	Anonymity	Last Checked
Kazakhstan	
199.189.250.69
1081	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
31.43.179.25
80	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
87.255.196.143
80	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
176.12.79.188
8888	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
88.204.142.108
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
176.12.76.169
3128	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
85.198.89.85
1439	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
176.12.73.245
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
188.94.159.26
3128	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
94.131.95.92
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
45.136.58.81
8443	
SOCKS5
Elite
2026-07-02 18:10 UTC
Kazakhstan	
31.43.179.110
80	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
46.8.252.15
8123	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
94.131.80.182
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
95.182.107.210
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
31.130.154.7
1080	
SOCKS4
Elite
2026-07-02 18:10 UTC
Kazakhstan	
193.124.93.99
10808	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
31.43.179.232
80	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
31.43.179.103
80	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
194.58.42.182
3128	
HTTP
Elite
2026-07-02 18:10 UTC

Country	IP	Port	Protocols	Anonymity	Last Checked
Kazakhstan	
193.193.240.36
48785	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
193.193.240.34
48785	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
5.188.154.149
8080	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
89.218.5.110
50733	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
87.76.35.238
4145	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.20.48.116
8080	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
45.94.23.145
3128	
HTTP
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
31.43.179.176
80	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
89.40.48.186
8080	
HTTPS
Elite
2026-07-02 18:10 UTC
Kazakhstan	
81.18.34.98
42535	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
185.146.3.129
1328	
HTTPS
Elite
2026-07-02 18:10 UTC
Kazakhstan	
46.36.132.23
8080	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
188.0.151.226
3629	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.169.36.228
1445	
SOCKS5
Elite
2026-07-02 18:10 UTC
Kazakhstan	
193.193.224.170
3128	
HTTPS
Elite
2026-07-02 18:10 UTC
Kazakhstan	
82.115.60.66
80	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
46.8.252.11
8123	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
37.228.65.107
32052	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
89.218.5.109
50733	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
188.0.138.11
8080	
HTTPS
Elite
2026-07-02 18:10 UTC

Country	IP	Port	Protocols	Anonymity	Last Checked
Kazakhstan	
217.196.20.150
8080	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
193.193.240.37
48785	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.218.5.106
50733	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
193.193.240.34
45944	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
37.77.128.162
8080	
HTTPS
Elite
2026-07-02 18:10 UTC
Kazakhstan	
89.218.5.108
50733	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.218.83.238
80	
HTTPS
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
192.159.39.30
3629	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
81.18.34.98
47680	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.218.170.58
41452	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.218.170.54
35704	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
82.200.181.54
3129	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
87.76.34.163
4145	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.218.170.54
41452	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.20.48.118
8080	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
92.47.62.133
1080	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
87.247.3.234
47247	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
37.228.65.107
51032	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
87.76.34.139
4145	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
91.185.3.126
8080	
HTTPS
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.218.169.122
4153	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
88.204.216.142
33156	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
87.76.34.49
4145	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.218.18.102
8080	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
176.110.125.233
51327	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.218.5.106
37717	
HTTP
Elite
2026-07-02 18:10 UTC
Kazakhstan	
85.159.25.62
8080	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
193.193.240.37
45944	
HTTPS
Elite
2026-07-02 18:10 UTC
Kazakhstan	
91.185.3.126
80	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
87.247.3.234
46511	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
217.11.79.234
8080	
HTTPS
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
85.159.27.112
3629	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
195.49.215.234
3629	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
87.76.34.28
4145	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
85.29.147.222
4145	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.218.170.58
35704	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
185.100.65.175
13004	
SOCKS4
Anonymous
2026-07-02 18:10 UTC
Kazakhstan	
89.218.5.110
37717	
HTTP
Transparent
2026-07-02 18:10 UTC
Kazakhstan	
89.218.5.109
37717	
HTTPS
Anonymous
2026-07-02 18:10 UTC
"""

new_proxies = []
for match in re.finditer(r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+(\d+)\s+(HTTP|HTTPS|SOCKS4|SOCKS5)', text, re.IGNORECASE):
    ip = match.group(1)
    port = match.group(2)
    proto = match.group(3).lower()
    if proto == 'https':
        proto = 'http'
    elif proto == 'socks4':
        proto = 'socks4' # playwright supports socks4 as socks4:// or socks5://? Wait, usually we can just leave it or cast to socks5 if unsupported. I'll keep socks4.
    new_proxies.append(f"{proto}://{ip}:{port}")

# Убираем дубли
new_proxies = list(dict.fromkeys(new_proxies))

with open('proxies.txt', 'a') as f:
    for p in new_proxies:
        f.write(p + "\n")

print(f"Added {len(new_proxies)} proxies.")
