#!/usr/bin/env python3
"""
Load test against a running server.

    UCM_MOCK=1 UCM_MOCK_NODES=15 UCM_MOCK_HZ=50 .venv/bin/python run.py &
    .venv/bin/python tests/load_test.py --viewers 50 --seconds 30

Each simulated viewer polls /api/raw the way the page does (with ETag).
Reports request counts, errors and latency.
"""

import argparse
import json
import statistics
import threading
import time
import urllib.error
import urllib.request


def viewer(base, stop_at, results):

    etag = None

    while time.time() < stop_at:
        request = urllib.request.Request(f"{base}/api/raw")
        if etag:
            request.add_header("If-None-Match", etag)

        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                json.loads(response.read())
                etag = response.headers.get("ETag")
                results["ok"].append(time.perf_counter() - started)
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                results["not_modified"].append(time.perf_counter() - started)
            else:
                results["errors"].append(f"HTTP {exc.code}")
        except Exception as exc:
            results["errors"].append(repr(exc))

        time.sleep(0.2)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:5002")
    parser.add_argument("--viewers", type=int, default=50)
    parser.add_argument("--seconds", type=int, default=30)
    args = parser.parse_args()

    results = {"ok": [], "not_modified": [], "errors": []}
    stop_at = time.time() + args.seconds

    threads = [threading.Thread(target=viewer, args=(args.base, stop_at, results))
               for _ in range(args.viewers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    latencies = sorted(results["ok"] + results["not_modified"])
    total = len(latencies) + len(results["errors"])

    print(f"requests: {total}  ok: {len(results['ok'])}  "
          f"304: {len(results['not_modified'])}  errors: {len(results['errors'])}")
    if latencies:
        p95 = latencies[int(len(latencies) * 0.95) - 1]
        print(f"latency ms  median: {statistics.median(latencies) * 1000:.1f}  "
              f"p95: {p95 * 1000:.1f}  max: {latencies[-1] * 1000:.1f}")
    for error in results["errors"][:5]:
        print("error:", error)

    with urllib.request.urlopen(f"{args.base}/healthz") as response:
        print("healthz:", response.read().decode())


if __name__ == "__main__":
    main()
