import time
import requests
import statistics

PROXIES = {
    "http": "http://localhost:8081",
    "https": "http://localhost:8081",
}

SITES = [
    "http://example.com",
    "http://ifconfig.me",
    "http://httpbin.org/get",
    "http://google.com", 
]

def benchmark_site(url):
    results = {"direct": [], "proxy": []}
    
    print(f"Testing {url}...")
    
    # Warmup
    try:
        requests.get(url, timeout=5)
        requests.get(url, proxies=PROXIES, timeout=5)
    except:
        pass

    # Measure Direct
    for _ in range(3):
        start = time.time()
        try:
            requests.get(url, timeout=5)
            duration = (time.time() - start) * 1000
            results["direct"].append(duration)
        except Exception as e:
            print(f"Direct Error {url}: {e}")

    # Measure Proxy
    for _ in range(3):
        start = time.time()
        try:
            requests.get(url, proxies=PROXIES, timeout=10)
            duration = (time.time() - start) * 1000
            results["proxy"].append(duration)
        except Exception as e:
            print(f"Proxy Error {url}: {e}")
            
    return results

print(f"{'Site':<30} | {'Direct (ms)':<12} | {'Proxy (ms)':<12} | {'Overhead':<10}")
print("-" * 75)

total_overhead = []

for site in SITES:
    res = benchmark_site(site)
    if res["direct"] and res["proxy"]:
        avg_direct = statistics.mean(res["direct"])
        avg_proxy = statistics.mean(res["proxy"])
        overhead = avg_proxy - avg_direct
        total_overhead.append(overhead)
        
        print(f"{site:<30} | {avg_direct:.1f}        | {avg_proxy:.1f}        | +{overhead:.1f} ms")
    else:
        print(f"{site:<30} | FAILED")

if total_overhead:
    print("-" * 75)
    print(f"Average Overhead: {statistics.mean(total_overhead):.2f} ms")
