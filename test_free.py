import urllib.request

def get_free_proxies():
    proxies = set()
    try:
        url = 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8')
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    proxies.add(f"http://{line}")
    except Exception as e:
        print("TheSpeedX error:", e)

    try:
        url = 'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8')
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    proxies.add(f"http://{line}")
    except Exception as e:
        print("monosans error:", e)
        
    print(f"Total global free proxies loaded: {len(proxies)}")
    
get_free_proxies()
