import requests

def test_endpoint(url):
    try:
        r = requests.get(url, timeout=5)
        print(f"URL: {url}")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Keys: {list(data.keys())}")
            if 'analysis' in data:
                print("Analysis data found!")
            elif 'insights' in data: # Backend Python
                print("Insights data found!")
        else:
            print(f"Error: {r.text[:200]}")
    except Exception as e:
        print(f"Failed to reach {url}: {e}")

print("--- Testing Next.js API ---")
test_endpoint("http://localhost:3000/api/analysis")

print("\n--- Testing Python Backend ---")
test_endpoint("http://localhost:8000/summary")
test_endpoint("http://localhost:8000/insights")
