import socket
import requests
import urllib3
import logging
import platform
import psutil
import os
import time
from typing import Dict, Any, List

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger('proxy_finder')

def check_internet_connection() -> Dict[str, Any]:
    """
    Check if there's a working internet connection.
    
    Returns:
        Dict[str, Any]: Connection status and details
    """
    result = {
        "connection_working": False,
        "google_reachable": False,
        "cloudflare_reachable": False,
        "dns_working": False,
        "errors": []
    }
    
    # Test DNS resolution
    try:
        socket.gethostbyname("www.google.com")
        result["dns_working"] = True
    except Exception as e:
        result["errors"].append(f"DNS resolution failed: {str(e)}")

    # Test common websites
    test_sites = [
        {"name": "google", "url": "https://www.google.com"},
        {"name": "cloudflare", "url": "https://1.1.1.1"}
    ]
    
    for site in test_sites:
        try:
            start_time = time.time()
            response = requests.get(site["url"], timeout=5)
            response_time = time.time() - start_time
            if response.status_code == 200:
                result[f"{site['name']}_reachable"] = True
                result[f"{site['name']}_response_time"] = round(response_time, 3)
        except Exception as e:
            result["errors"].append(f"Failed to reach {site['name']}: {str(e)}")
    
    # Set overall connection status
    result["connection_working"] = result["google_reachable"] or result["cloudflare_reachable"]
    
    return result

def check_test_endpoints() -> Dict[str, Any]:
    """
    Check if proxy testing endpoints are working.
    
    Returns:
        Dict[str, Any]: Endpoint status details
    """
    result = {
        "endpoints": {},
        "working_count": 0,
        "total_count": 0
    }
    
    test_endpoints = [
        {"name": "httpbin", "url": "http://httpbin.org/ip"},
        {"name": "ip-api", "url": "http://ip-api.com/json"},
        {"name": "ifconfig.me", "url": "http://ifconfig.me/ip"},
        {"name": "example.com", "url": "http://example.com"}
    ]
    
    for endpoint in test_endpoints:
        result["total_count"] += 1
        endpoint_result = {
            "working": False,
            "response_time": None,
            "error": None
        }
        
        try:
            start_time = time.time()
            response = requests.get(endpoint["url"], timeout=5)
            response_time = time.time() - start_time
            endpoint_result["response_time"] = round(response_time, 3)
            
            if response.status_code == 200:
                endpoint_result["working"] = True
                result["working_count"] += 1
        except Exception as e:
            endpoint_result["error"] = str(e)
        
        result["endpoints"][endpoint["name"]] = endpoint_result
    
    return result

def get_system_info() -> Dict[str, Any]:
    """
    Get system information for debugging.
    
    Returns:
        Dict[str, Any]: System information
    """
    result = {
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "memory_usage_percent": psutil.virtual_memory().percent,
        "cpu_usage_percent": psutil.cpu_percent(interval=0.1),
        "network_interfaces": []
    }
    
    # Get network interfaces
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                result["network_interfaces"].append({
                    "name": iface,
                    "ip": addr.address,
                    "netmask": addr.netmask
                })
                break
    
    return result

def run_diagnostics() -> Dict[str, Any]:
    """
    Run comprehensive diagnostics for proxy finder.
    
    Returns:
        Dict[str, Any]: Diagnostic results
    """
    logger.info("Running diagnostics...")
    
    diagnostics = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "internet_connection": check_internet_connection(),
        "test_endpoints": check_test_endpoints(),
        "system_info": get_system_info()
    }
    
    # Log summary
    conn_status = "UP" if diagnostics["internet_connection"]["connection_working"] else "DOWN"
    endpoints_status = f"{diagnostics['test_endpoints']['working_count']}/{diagnostics['test_endpoints']['total_count']} working"
    
    logger.info(f"Diagnostics complete - Internet: {conn_status}, Endpoints: {endpoints_status}")
    
    return diagnostics 