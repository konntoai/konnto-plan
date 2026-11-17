"""
KONNTO AI Backend API Testing - Iteration 4
Tests specific fixes for partner leak and permission boundaries
"""
import sys
import requests
import json
from datetime import datetime

# Public endpoint from frontend/.env
BASE_URL = "https://konnto-plan--87psd4r7.preview.emergentagent.com/api"

# Demo credentials
DEMO_ACCOUNTS = {
    "owner": {"email": "demo.owner+clerk_test@konnto.ai", "name": "Arjun Mehra"},
    "priya": {"email": "demo.priya+clerk_test@konnto.ai", "name": "Priya Nair"},
    "supplier": {"email": "demo.supplier+clerk_test@konnto.ai", "name": "Rajesh Gupta"},
}

class KONNTOTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tokens = {}
        self.issues = []
        
    def log(self, msg, level="INFO"):
        prefix = "✅" if level == "PASS" else "❌" if level == "FAIL" else "🔍"
        print(f"{prefix} {msg}")
        
    def test(self, name, condition, error_msg=""):
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            self.log(f"PASS: {name}", "PASS")
            return True
        else:
            self.log(f"FAIL: {name} - {error_msg}", "FAIL")
            self.issues.append(f"{name}: {error_msg}")
            return False
    
    def get_clerk_token(self, email):
        """Mint a Clerk token for testing"""
        try:
            import subprocess
            cmd = f"cd /app/tests && python3 -c \"import sys;sys.path.insert(0,'/app/tests');from clerk_token import *;import requests;u=bapi('/users?email_address='+requests.utils.quote('{email}'),method='GET')[0];print(token_for(u['id']))\""
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                self.log(f"Failed to get token for {email}: {result.stderr}", "FAIL")
                return None
        except Exception as e:
            self.log(f"Error getting token for {email}: {e}", "FAIL")
            return None
    
    def api_call(self, method, endpoint, token=None, data=None, expect_status=200):
        """Make API call and return response"""
        url = f"{BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=15)
            elif method == "POST":
                resp = requests.post(url, headers=headers, json=data, timeout=15)
            elif method == "PUT":
                resp = requests.put(url, headers=headers, json=data, timeout=15)
            elif method == "DELETE":
                resp = requests.delete(url, headers=headers, timeout=15)
            else:
                return None, None
            
            return resp.status_code, resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        except Exception as e:
            self.log(f"API call failed: {method} {endpoint} - {e}", "FAIL")
            return None, str(e)
    
    def test_fix1_partner_leak(self):
        """FIX 1: Test that supplier only sees limited members (Arjun + Rajesh)"""
        self.log("\n=== Testing FIX 1: Partner Leak (Supplier should see only 2 members) ===")
        
        token = self.get_clerk_token(DEMO_ACCOUNTS["supplier"]["email"])
        if not token:
            self.test("Supplier token generation", False, "Could not generate token")
            return
        self.tokens["supplier"] = token
        self.test("Supplier token generation", True)
        
        # Test /api/members - should return only 2 members
        status, data = self.api_call("GET", "/members", token)
        self.test("Supplier /members endpoint returns 200", status == 200, f"Status: {status}")
        
        if status == 200:
            members = data.get("members", [])
            member_count = len(members)
            self.test("Supplier sees only 2 members (not all 8)", 
                     member_count == 2, 
                     f"Expected 2, got {member_count}")
            
            # Check that only Arjun Mehra (owner) and Rajesh Gupta (supplier) are visible
            member_names = [m.get("name") for m in members]
            self.test("Supplier sees Arjun Mehra (owner)", 
                     "Arjun Mehra" in member_names,
                     f"Members: {member_names}")
            self.test("Supplier sees Rajesh Gupta (self)", 
                     "Rajesh Gupta" in member_names,
                     f"Members: {member_names}")
            
            # Verify supplier does NOT see other team members
            other_members = ["Priya Nair", "Ramesh Kumar", "Suresh Yadav", "Anita Desai"]
            for name in other_members:
                self.test(f"Supplier does NOT see {name}", 
                         name not in member_names,
                         f"Should not see {name} but found in: {member_names}")
        
        # Test dashboard - people count should be 2
        status, data = self.api_call("GET", "/dashboard", token)
        if status == 200:
            team_count = data.get("counts", {}).get("team", 0)
            self.test("Supplier dashboard shows 2 people", 
                     team_count == 2,
                     f"Expected 2, got {team_count}")
        
        # Test creating thread with unauthorized member (should fail)
        # Get a member ID that supplier shouldn't see (Priya)
        owner_token = self.get_clerk_token(DEMO_ACCOUNTS["owner"]["email"])
        if owner_token:
            status, owner_data = self.api_call("GET", "/members", owner_token)
            if status == 200:
                all_members = owner_data.get("members", [])
                priya = next((m for m in all_members if "Priya" in m.get("name", "")), None)
                if priya:
                    # Try to create thread with Priya as supplier (should fail)
                    status, data = self.api_call("POST", "/threads", token, 
                                                {"member_ids": [priya["member_id"]]})
                    self.test("Supplier cannot create thread with unauthorized member",
                             status == 400,
                             f"Expected 400, got {status}. Should fail with 'Pick at least one person'")
    
    def test_owner_dashboard(self):
        """Test owner dashboard for approval count"""
        self.log("\n=== Testing Owner Dashboard (for approval count) ===")
        
        token = self.get_clerk_token(DEMO_ACCOUNTS["owner"]["email"])
        if not token:
            return
        
        status, data = self.api_call("GET", "/dashboard", token)
        if status == 200:
            approval_count = data.get("counts", {}).get("approvals", 0)
            self.log(f"Owner sees {approval_count} pending approvals")
            self.test("Owner has pending approvals", approval_count > 0)
    
    def test_priya_permissions(self):
        """Test Priya's permission boundaries"""
        self.log("\n=== Testing Priya (Team Lead) Permissions ===")
        
        token = self.get_clerk_token(DEMO_ACCOUNTS["priya"]["email"])
        if not token:
            return
        self.tokens["priya"] = token
        
        # Test knowledge endpoint - should NOT see finance facts
        status, data = self.api_call("GET", "/knowledge", token)
        if status == 200:
            facts = data.get("facts", [])
            finance_facts = [f for f in facts if f.get("category") in ["finance", "money"]]
            self.test("Priya does NOT see finance facts",
                     len(finance_facts) == 0,
                     f"Found {len(finance_facts)} finance facts")
        
        # Test documents - should NOT see private owner documents
        status, data = self.api_call("GET", "/documents", token)
        if status == 200:
            docs = data.get("documents", [])
            private_doc = next((d for d in docs if "Owner_Cashflow" in d.get("filename", "")), None)
            self.test("Priya does NOT see Owner_Cashflow_Notes.txt",
                     private_doc is None,
                     f"Should not see private owner document")
    
    def run_all_tests(self):
        """Run all backend tests"""
        self.log("=" * 60)
        self.log("KONNTO AI Backend Testing - Iteration 4")
        self.log("Testing specific fixes for partner leak and permissions")
        self.log("=" * 60)
        
        try:
            self.test_fix1_partner_leak()
            self.test_owner_dashboard()
            self.test_priya_permissions()
        except Exception as e:
            self.log(f"Test suite error: {e}", "FAIL")
        
        # Print summary
        self.log("\n" + "=" * 60)
        self.log(f"BACKEND TESTS COMPLETE: {self.tests_passed}/{self.tests_run} passed")
        self.log("=" * 60)
        
        if self.issues:
            self.log("\n⚠️  Issues found:")
            for issue in self.issues:
                self.log(f"  - {issue}")
        
        return 0 if self.tests_passed == self.tests_run else 1

if __name__ == "__main__":
    tester = KONNTOTester()
    sys.exit(tester.run_all_tests())
