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

    return results

def measure_throughput(url_file, size_mb):
    print(f"Testing Throughput on {url_file} (~{size_mb} MB)...")
    
    # Direct
    start = time.time()
    try:
        r = requests.get(url_file, timeout=30)
        size_bytes = len(r.content)
        duration_s = time.time() - start
        mb_s_direct = (size_bytes / 1024 / 1024) / duration_s
    except Exception as e:
        print(f"Direct Throughput Error: {e}")
        mb_s_direct = 0

    # Proxy
    start = time.time()
    try:
        r = requests.get(url_file, proxies=PROXIES, timeout=30)
        size_bytes = len(r.content)
        duration_s = time.time() - start
        mb_s_proxy = (size_bytes / 1024 / 1024) / duration_s
    except Exception as e:
        print(f"Proxy Throughput Error: {e}")
        mb_s_proxy = 0
        
    return mb_s_direct, mb_s_proxy

print(f"\n--- 1. LATENCY (Délai) ---")
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
        
        sign = "+" if overhead > 0 else ""
        print(f"{site:<30} | {avg_direct:.1f}        | {avg_proxy:.1f}        | {sign}{overhead:.1f} ms")
    else:
        print(f"{site:<30} | FAILED")

if total_overhead:
    print("-" * 75)
    print(f"Average Overhead: {statistics.mean(total_overhead):.2f} ms")



print(f"\n--- 2. THROUGHPUT (Débit) per Site ---")
print(f"{'Site':<30} | {'Direct':<15} | {'Proxy':<15}")
print("-" * 75)

for site in SITES:
    # Use the existing function but for these sites
    # Note: These are small pages, so speed might be dominated by latency
    d_mb, p_mb = measure_throughput(site, 0) # 0 means size unknown/irrelevant for print
    
    # Convert to KB/s for readability since pages are small
    d_kb = d_mb * 1024
    p_kb = p_mb * 1024
    
    if d_mb == 0 and p_mb == 0:
         print(f"{site:<30} | FAILED          | FAILED")
    else:
         print(f"{site:<30} | {d_kb:.1f} KB/s       | {p_kb:.1f} KB/s")
    
print(f"\n--- 3. THROUGHPUT (Débit) on Large File (1MB) ---")
# Test with a 1MB file
LARGE_FILE = "http://httpbin.org/bytes/1048576" 

direct_mb_s, proxy_mb_s = measure_throughput(LARGE_FILE, 1)

# Convert to KB/s for better precision if slow
direct_kb_s = direct_mb_s * 1024
proxy_kb_s = proxy_mb_s * 1024

print(f"\n{'Metric':<20} | {'Direct':<15} | {'Proxy':<15} | {'Loss (%)':<10}")
print("-" * 70)
print(f"{'Speed (MB/s)':<20} | {direct_mb_s:.4f} MB/s    | {proxy_mb_s:.4f} MB/s    | -{100 - (proxy_mb_s/direct_mb_s*100) if direct_mb_s > 0 else 0:.1f}%")
print(f"{'Speed (KB/s)':<20} | {direct_kb_s:.1f} KB/s     | {proxy_kb_s:.1f} KB/s     |")
 



