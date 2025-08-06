#!/usr/bin/env python3
"""
Test FastField API Structure
Explore the API to find correct endpoints and parameters
"""

import requests
from requests.auth import HTTPBasicAuth
import json

class FastFieldAPITester:
    def __init__(self):
        # FastField API credentials
        self.username = "IT@skytecpro.com"
        self.password = "Skytec@2326"
        self.api_key = "FF-6862225545423a0805de9e91cad840b6_0_e4f35151cd453855a4bb9bfde64ed71b"
        self.form_id = "1143703"  # Comcast QC Form New
        
        # FastField API endpoints
        self.auth_url = "https://manage.fastfieldforms.com/api/authenticate"
        self.session_token = None
        
    def authenticate_fastfield(self):
        """Authenticate with FastField API"""
        print("🔐 Authenticating with FastField API...")
        
        try:
            response = requests.post(
                self.auth_url, 
                auth=HTTPBasicAuth(self.username, self.password)
            )
            
            if response.status_code == 200:
                data = json.loads(response.content)
                self.session_token = data['data']['sessionToken']
                print(f"✅ FastField authentication successful!")
                print(f"   Session Token: {self.session_token[:20]}...")
                return True
            else:
                print(f"❌ FastField authentication failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error authenticating with FastField: {str(e)}")
            return False
    
    def test_api_endpoints(self):
        """Test different API endpoints"""
        print("\n🔍 Testing FastField API endpoints...")
        
        headers = {
            "Authorization": f"Bearer {self.session_token}",
            "X-Gatekeeper-SessionToken": self.session_token,
            "FastField-API-Key": self.api_key
        }
        
        # Test different endpoints
        endpoints_to_test = [
            {
                'name': 'Submissions (v3)',
                'url': 'https://api.fastfieldforms.com/services/v3/submissions',
                'params': {}
            },
            {
                'name': 'Submissions (v2)',
                'url': 'https://api.fastfieldforms.com/services/v2/submissions',
                'params': {}
            },
            {
                'name': 'Forms',
                'url': 'https://api.fastfieldforms.com/services/v3/forms',
                'params': {}
            },
            {
                'name': 'Forms (v2)',
                'url': 'https://api.fastfieldforms.com/services/v2/forms',
                'params': {}
            },
            {
                'name': 'Projects',
                'url': 'https://api.fastfieldforms.com/services/v3/projects',
                'params': {}
            },
            {
                'name': 'Projects (v2)',
                'url': 'https://api.fastfieldforms.com/services/v2/projects',
                'params': {}
            }
        ]
        
        for endpoint in endpoints_to_test:
            print(f"\n--- Testing {endpoint['name']} ---")
            try:
                response = requests.get(endpoint['url'], headers=headers, params=endpoint['params'])
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Success! Found {len(data.get('data', []))} items")
                    if 'data' in data and len(data['data']) > 0:
                        print(f"Sample item keys: {list(data['data'][0].keys())}")
                else:
                    print(f"❌ Failed: {response.text}")
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
    def test_form_specific_endpoints(self):
        """Test form-specific endpoints"""
        print("\n🔍 Testing form-specific endpoints...")
        
        headers = {
            "Authorization": f"Bearer {self.session_token}",
            "X-Gatekeeper-SessionToken": self.session_token,
            "FastField-API-Key": self.api_key
        }
        
        # Test different form-specific endpoints
        form_endpoints = [
            {
                'name': 'Form Submissions (v3)',
                'url': f'https://api.fastfieldforms.com/services/v3/forms/{self.form_id}/submissions',
                'params': {}
            },
            {
                'name': 'Form Submissions (v2)',
                'url': f'https://api.fastfieldforms.com/services/v2/forms/{self.form_id}/submissions',
                'params': {}
            },
            {
                'name': 'Form Details (v3)',
                'url': f'https://api.fastfieldforms.com/services/v3/forms/{self.form_id}',
                'params': {}
            },
            {
                'name': 'Form Details (v2)',
                'url': f'https://api.fastfieldforms.com/services/v2/forms/{self.form_id}',
                'params': {}
            },
            {
                'name': 'Submissions with Form Filter (v3)',
                'url': 'https://api.fastfieldforms.com/services/v3/submissions',
                'params': {'formId': self.form_id}
            },
            {
                'name': 'Submissions with Form Filter (v2)',
                'url': 'https://api.fastfieldforms.com/services/v2/submissions',
                'params': {'formId': self.form_id}
            }
        ]
        
        for endpoint in form_endpoints:
            print(f"\n--- Testing {endpoint['name']} ---")
            try:
                response = requests.get(endpoint['url'], headers=headers, params=endpoint['params'])
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Success!")
                    if 'data' in data:
                        print(f"Found {len(data['data'])} items")
                        if len(data['data']) > 0:
                            print(f"Sample item keys: {list(data['data'][0].keys())}")
                    elif 'submissions' in data:
                        print(f"Found {len(data['submissions'])} submissions")
                        if len(data['submissions']) > 0:
                            print(f"Sample submission keys: {list(data['submissions'][0].keys())}")
                else:
                    print(f"❌ Failed: {response.text}")
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
    def test_manage_endpoints(self):
        """Test manage.fastfieldforms.com endpoints"""
        print("\n🔍 Testing manage.fastfieldforms.com endpoints...")
        
        headers = {
            "Authorization": f"Bearer {self.session_token}",
            "X-Gatekeeper-SessionToken": self.session_token,
            "FastField-API-Key": self.api_key
        }
        
        # Test manage endpoints
        manage_endpoints = [
            {
                'name': 'Forms (Manage)',
                'url': 'https://manage.fastfieldforms.com/api/forms',
                'params': {}
            },
            {
                'name': 'Submissions (Manage)',
                'url': 'https://manage.fastfieldforms.com/api/submissions',
                'params': {}
            },
            {
                'name': 'Form Submissions (Manage)',
                'url': f'https://manage.fastfieldforms.com/api/forms/{self.form_id}/submissions',
                'params': {}
            }
        ]
        
        for endpoint in manage_endpoints:
            print(f"\n--- Testing {endpoint['name']} ---")
            try:
                response = requests.get(endpoint['url'], headers=headers, params=endpoint['params'])
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Success!")
                    if 'data' in data:
                        print(f"Found {len(data['data'])} items")
                        if len(data['data']) > 0:
                            print(f"Sample item keys: {list(data['data'][0].keys())}")
                else:
                    print(f"❌ Failed: {response.text}")
            except Exception as e:
                print(f"❌ Error: {str(e)}")
    
    def run_tests(self):
        """Run all API tests"""
        print("🚀 FastField API Structure Test")
        print("=" * 50)
        
        # Authenticate first
        if not self.authenticate_fastfield():
            print("❌ Authentication failed - stopping tests")
            return
        
        # Test general endpoints
        self.test_api_endpoints()
        
        # Test form-specific endpoints
        self.test_form_specific_endpoints()
        
        # Test manage endpoints
        self.test_manage_endpoints()
        
        print("\n�� API Structure Test Complete!")
        print("Check the output above to find the correct endpoints and parameters.")

def main():
    """Main function"""
    tester = FastFieldAPITester()
    tester.run_tests()

if __name__ == "__main__":
    main()
