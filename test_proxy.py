#!/usr/bin/env python
"""
Simple script to test a single proxy
"""
import sys
import os
import socket
import requests
import time

def test_proxy(proxy_str):
    """Test if a proxy is working by trying to connect to it"""
    print(f"Testing proxy: {proxy_str}")
    
    # 1. Test socket connection
    try:
        host, port = proxy_str.split(':')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        print(f"Attempting to connect to socket {host}:{port}...")
        sock.connect((host, int(port)))
        sock.close()
        print("[SUCCESS] Socket connection successful")
    except Exception as e:
        print(f"[FAILED] Socket connection failed: {e}")
        return False
    
    # 2. Test HTTP request
    proxies = {
        'http': f'http://{proxy_str}',
        'https': f'http://{proxy_str}'
    }
    
    test_urls = [
        'http://httpbin.org/ip',
        'http://ip-api.com/json',
        'http://ifconfig.me/ip',
        'http://www.example.com'
    ]
    
    for url in test_urls:
        try:
            print(f"Testing HTTP request to {url}...")
            start_time = time.time()
            response = requests.get(url, proxies=proxies, timeout=10, verify=False)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                print(f"[SUCCESS] HTTP request successful ({elapsed:.2f}s)")
                print(f"Response: {response.text[:100]}...")
                return True
            else:
                print(f"[FAILED] HTTP request failed with status code: {response.status_code}")
        except Exception as e:
            print(f"[FAILED] HTTP request failed: {e}")
    
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_proxy.py IP:PORT")
        sys.exit(1)
    
    proxy = sys.argv[1]
    test_proxy(proxy)
