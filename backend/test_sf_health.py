"""
Test script for Salesforce Health Check API

This script tests the Salesforce health check endpoint and displays
the connection status in a user-friendly format.
"""

import requests
import json
from datetime import datetime


def test_health_check(base_url="http://localhost:8000"):
    """Test the Salesforce health check endpoint"""
    
    endpoint = f"{base_url}/api/v1/salesforce/health"
    
    print("=" * 60)
    print("SALESFORCE HEALTH CHECK TEST")
    print("=" * 60)
    print(f"Testing endpoint: {endpoint}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("-" * 60)
    
    try:
        response = requests.get(endpoint, timeout=10)
        response.raise_for_status()
        
        health_data = response.json()
        
        # Display results
        print(f"\n📊 Status: {health_data.get('status', 'unknown').upper()}")
        print(f"🔗 Connected: {'✅ YES' if health_data.get('connected') else '❌ NO'}")
        print(f"💬 Message: {health_data.get('message', 'No message')}")
        
        # Show details if connected
        if health_data.get('connected') and 'details' in health_data:
            details = health_data['details']
            print("\n📋 Connection Details:")
            print(f"   • Instance URL: {details.get('instance_url', 'N/A')}")
            print(f"   • API Version: {details.get('api_version', 'N/A')}")
            print(f"   • Session Active: {'✅' if details.get('session_active') else '❌'}")
            print(f"   • Query Test: {details.get('query_test', 'N/A')}")
        
        # Show error if present
        if 'error' in health_data:
            print("\n⚠️  Error Information:")
            print(f"   • Error: {health_data.get('error', 'Unknown error')}")
            if 'error_type' in health_data:
                print(f"   • Error Type: {health_data.get('error_type')}")
        
        print("\n" + "-" * 60)
        print("📄 Full Response:")
        print(json.dumps(health_data, indent=2, default=str))
        print("=" * 60)
        
        # Return success/failure
        return health_data.get('connected', False)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend server")
        print("   Make sure the backend is running on", base_url)
        print("   Start it with: python -m uvicorn app.main:app --reload")
        return False
        
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timed out")
        print("   The server is not responding")
        return False
        
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP ERROR: {e}")
        print(f"   Status Code: {response.status_code}")
        try:
            print(f"   Response: {response.text}")
        except:
            pass
        return False
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    
    # Allow custom base URL as command-line argument
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    # Run the test
    success = test_health_check(base_url)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
