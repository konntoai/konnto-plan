"""
KONNTO AI Backend API Testing
Tests all demo account functionalities and permission boundaries
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
    
    def test_owner_access(self):
        """Test owner account - full access"""
        self.log("\n=== Testing OWNER Account (Arjun Mehra) ===")
        
        token = self.get_clerk_token(DEMO_ACCOUNTS["owner"]["email"])
        if not token:
            self.test("Owner token generation", False, "Could not generate token")
            return
        self.tokens["owner"] = token
        self.test("Owner token generation", True)
        
        # Test /me endpoint
        status, data = self.api_call("GET", "/me", token)
        self.test("Owner /me endpoint", status == 200, f"Status: {status}")
        if status == 200:
            self.test("Owner has member data", data.get("member") is not None)
            self.test("Owner org name is 'Mehra Build Supplies'", 
                     data.get("org", {}).get("name") == "Mehra Build Supplies")
        
        # Test dashboard
        status, data = self.api_call("GET", "/dashboard", token)
        self.test("Owner dashboard access", status == 200, f"Status: {status}")
        if status == 200:
            counts = data.get("counts", {})
            self.test("Dashboard has overdue count", "overdue" in counts)
            self.test("Dashboard overdue = 3", counts.get("overdue") == 3, 
                     f"Expected 3, got {counts.get('overdue')}")
            self.test("Dashboard stuck = 1", counts.get("stuck") == 1,
                     f"Expected 1, got {counts.get('stuck')}")
            self.test("Dashboard done_week = 4", counts.get("done_week") == 4,
                     f"Expected 4, got {counts.get('done_week')}")
            self.test("Dashboard approvals = 5", counts.get("approvals") == 5,
                     f"Expected 5, got {counts.get('approvals')}")
            self.test("Dashboard people = 7", counts.get("team") == 7,
                     f"Expected 7, got {counts.get('team')}")
            
            # Check brief renders markdown properly (no literal **)
            brief = data.get("brief", {})
            if brief.get("text"):
                self.test("Brief text does not contain literal **", 
                         "**" not in brief["text"] or brief["text"].count("**") % 2 == 0,
                         "Found unmatched ** in brief text")
        
        # Test work items
        status, data = self.api_call("GET", "/items", token)
        self.test("Owner work items access", status == 200, f"Status: {status}")
        if status == 200:
            items = data.get("items", [])
            self.test("Owner sees 22 work items", len(items) == 22,
                     f"Expected 22, got {len(items)}")
        
        # Test approvals
        status, data = self.api_call("GET", "/approvals?status=pending", token)
        self.test("Owner approvals access", status == 200, f"Status: {status}")
        if status == 200:
            approvals = data.get("approvals", [])
            self.test("Owner sees 5 pending approvals", len(approvals) == 5,
                     f"Expected 5, got {len(approvals)}")
            self.test("Owner can_decide approvals", data.get("can_decide") == True)
        
        # Test team
        status, data = self.api_call("GET", "/members", token)
        self.test("Owner team access", status == 200, f"Status: {status}")
        if status == 200:
            members = data.get("members", [])
            active = [m for m in members if m.get("status") == "active"]
            invited = [m for m in members if m.get("status") == "invited"]
            self.test("Owner sees 7 active members", len(active) == 7,
                     f"Expected 7, got {len(active)}")
            self.test("Owner sees 1 invited member", len(invited) == 1,
                     f"Expected 1, got {len(invited)}")
        
        # Test documents
        status, data = self.api_call("GET", "/documents", token)
        self.test("Owner documents access", status == 200, f"Status: {status}")
        if status == 200:
            docs = data.get("documents", [])
            self.test("Owner sees 4 documents", len(docs) == 4,
                     f"Expected 4, got {len(docs)}")
            # Check for private doc
            private_doc = any(d.get("filename") == "Owner_Cashflow_Notes.txt" for d in docs)
            self.test("Owner sees private Owner_Cashflow_Notes.txt", private_doc)
        
        # Test knowledge
        status, data = self.api_call("GET", "/knowledge", token)
        self.test("Owner knowledge access", status == 200, f"Status: {status}")
        if status == 200:
            facts = data.get("facts", [])
            rules = data.get("rules", [])
            self.test("Owner sees 9 facts", len(facts) == 9,
                     f"Expected 9, got {len(facts)}")
            self.test("Owner sees 5 rules", len(rules) == 5,
                     f"Expected 5, got {len(rules)}")
        
        # Test chat messages
        status, data = self.api_call("GET", "/chat/messages", token)
        self.test("Owner chat messages access", status == 200, f"Status: {status}")
        if status == 200:
            messages = data.get("messages", [])
            self.test("Owner has chat history", len(messages) > 0)
            
            # Check for approval notice with buttons
            approval_notices = [m for m in messages if m.get("kind") == "approval" and m.get("buttons")]
            self.test("Owner has approval notice with buttons", len(approval_notices) > 0,
                     "Expected at least 1 approval notice with buttons")
            
            # Check for DRAFT cards
            draft_cards = [m for m in messages if any(c.get("status") == "draft" for c in m.get("cards", []))]
            self.test("Owner has messages with DRAFT cards", len(draft_cards) > 0)
            
            # Check for PENDING handover card
            pending_handover = [m for m in messages if any(c.get("type") == "handover" and c.get("status") == "pending" for c in m.get("cards", []))]
            self.test("Owner has PENDING handover card", len(pending_handover) > 0)
    
    def test_priya_access(self):
        """Test team lead account - limited permissions"""
        self.log("\n=== Testing TEAM LEAD Account (Priya Nair) ===")
        
        token = self.get_clerk_token(DEMO_ACCOUNTS["priya"]["email"])
        if not token:
            self.test("Priya token generation", False, "Could not generate token")
            return
        self.tokens["priya"] = token
        self.test("Priya token generation", True)
        
        # Test /me endpoint
        status, data = self.api_call("GET", "/me", token)
        self.test("Priya /me endpoint", status == 200, f"Status: {status}")
        if status == 200:
            member = data.get("member", {})
            access = member.get("access", [])
            self.test("Priya has own_work access", "own_work" in access)
            self.test("Priya has team_work access", "team_work" in access)
            self.test("Priya has documents access", "documents" in access)
            self.test("Priya has manage_team access", "manage_team" in access)
            self.test("Priya does NOT have money access", "money" not in access)
            self.test("Priya does NOT have approve access", "approve" not in access)
        
        # Test knowledge - should NOT see finance facts
        status, data = self.api_call("GET", "/knowledge", token)
        self.test("Priya knowledge access", status == 200, f"Status: {status}")
        if status == 200:
            facts = data.get("facts", [])
            self.test("Priya sees 6 facts (not 9)", len(facts) == 6,
                     f"Expected 6 (no finance facts), got {len(facts)}")
            
            # Check that finance facts are hidden
            finance_facts = [f for f in facts if "margin" in f.get("text", "").lower() or 
                           "cash in bank" in f.get("text", "").lower() or
                           "credit limit" in f.get("text", "").lower()]
            self.test("Priya does NOT see finance facts", len(finance_facts) == 0,
                     f"Found {len(finance_facts)} finance facts")
        
        # Test documents - should NOT see private owner doc
        status, data = self.api_call("GET", "/documents", token)
        self.test("Priya documents access", status == 200, f"Status: {status}")
        if status == 200:
            docs = data.get("documents", [])
            private_doc = any(d.get("filename") == "Owner_Cashflow_Notes.txt" for d in docs)
            self.test("Priya does NOT see Owner_Cashflow_Notes.txt", not private_doc,
                     "Priya should not see owner's private document")
        
        # Test work items - amounts should be hidden on others' items
        status, data = self.api_call("GET", "/items", token)
        self.test("Priya work items access", status == 200, f"Status: {status}")
        if status == 200:
            items = data.get("items", [])
            # Check for amount_hidden flag on items not assigned to Priya
            others_items = [i for i in items if i.get("assignee_name") != "Priya Nair" and i.get("amount") is not None]
            if others_items:
                hidden_amounts = [i for i in others_items if i.get("amount_hidden")]
                self.test("Amounts hidden on others' items", len(hidden_amounts) > 0,
                         f"Expected some items with amount_hidden, found {len(hidden_amounts)}")
        
        # Test approvals - should only see her own requests
        status, data = self.api_call("GET", "/approvals?status=pending", token)
        self.test("Priya approvals access", status == 200, f"Status: {status}")
        if status == 200:
            approvals = data.get("approvals", [])
            self.test("Priya sees only her 2 requests", len(approvals) == 2,
                     f"Expected 2, got {len(approvals)}")
            self.test("Priya can_decide is False", data.get("can_decide") == False)
        
        # Test chat messages - should have task notice with buttons
        status, data = self.api_call("GET", "/chat/messages", token)
        self.test("Priya chat messages access", status == 200, f"Status: {status}")
        if status == 200:
            messages = data.get("messages", [])
            task_notices = [m for m in messages if m.get("kind") == "task" and m.get("buttons")]
            self.test("Priya has task notice with Done/Delayed/Need help buttons", 
                     len(task_notices) > 0)
    
    def test_supplier_access(self):
        """Test supplier/partner account - very limited access"""
        self.log("\n=== Testing SUPPLIER Account (Rajesh Gupta) ===")
        
        token = self.get_clerk_token(DEMO_ACCOUNTS["supplier"]["email"])
        if not token:
            self.test("Supplier token generation", False, "Could not generate token")
            return
        self.tokens["supplier"] = token
        self.test("Supplier token generation", True)
        
        # Test /me endpoint
        status, data = self.api_call("GET", "/me", token)
        self.test("Supplier /me endpoint", status == 200, f"Status: {status}")
        if status == 200:
            member = data.get("member", {})
            self.test("Supplier member_type is 'partner'", 
                     member.get("member_type") == "partner")
        
        # Test work items - should see only 1 item
        status, data = self.api_call("GET", "/items", token)
        self.test("Supplier work items access", status == 200, f"Status: {status}")
        if status == 200:
            items = data.get("items", [])
            self.test("Supplier sees only 1 work item", len(items) == 1,
                     f"Expected 1, got {len(items)}")
            if len(items) == 1:
                self.test("Supplier's item is 'Deliver 500 bags'",
                         "500 bags" in items[0].get("title", ""))
        
        # Test projects - should only see projects with visible items
        status, data = self.api_call("GET", "/projects", token)
        self.test("Supplier projects access", status == 200, f"Status: {status}")
        if status == 200:
            projects = data.get("projects", [])
            self.test("Supplier sees only 1 project", len(projects) == 1,
                     f"Expected 1 (Mehta Tower), got {len(projects)}")
            if len(projects) == 1:
                self.test("Supplier's project is 'Mehta Tower — Phase 2 supply'",
                         "Mehta Tower" in projects[0].get("name", ""))
        
        # Test documents - should see 0 docs
        status, data = self.api_call("GET", "/documents", token)
        self.test("Supplier documents access", status == 200, f"Status: {status}")
        if status == 200:
            docs = data.get("documents", [])
            self.test("Supplier sees 0 documents", len(docs) == 0,
                     f"Expected 0, got {len(docs)}")
        
        # Test knowledge - should see only 2 facts shared with partners
        status, data = self.api_call("GET", "/knowledge", token)
        self.test("Supplier knowledge access", status == 200, f"Status: {status}")
        if status == 200:
            facts = data.get("facts", [])
            rules = data.get("rules", [])
            self.test("Supplier sees only 2 facts", len(facts) == 2,
                     f"Expected 2 (shared with partners), got {len(facts)}")
            self.test("Supplier sees 0 rules", len(rules) == 0,
                     f"Expected 0, got {len(rules)}")
        
        # Test approvals - should see none
        status, data = self.api_call("GET", "/approvals", token)
        self.test("Supplier approvals access", status == 200, f"Status: {status}")
        if status == 200:
            approvals = data.get("approvals", [])
            self.test("Supplier sees 0 approvals", len(approvals) == 0,
                     f"Expected 0, got {len(approvals)}")
        
        # Test team - should only see owner and thread participants
        status, data = self.api_call("GET", "/members", token)
        self.test("Supplier team access", status == 200, f"Status: {status}")
        if status == 200:
            members = data.get("members", [])
            # Supplier should see: owner (Arjun), himself, and maybe his inviter
            self.test("Supplier sees limited team members", len(members) <= 3,
                     f"Expected ≤3, got {len(members)}")
    
    def test_chat_action_buttons(self):
        """Test approval notice button functionality"""
        self.log("\n=== Testing Chat Action Buttons ===")
        
        if "owner" not in self.tokens:
            self.log("Skipping button tests - owner token not available")
            return
        
        token = self.tokens["owner"]
        
        # Get chat messages to find approval notice
        status, data = self.api_call("GET", "/chat/messages", token)
        if status != 200:
            self.test("Get chat messages for button test", False, f"Status: {status}")
            return
        
        messages = data.get("messages", [])
        approval_msg = None
        for m in messages:
            if m.get("kind") == "approval" and m.get("buttons") and not m.get("buttons_used"):
                approval_msg = m
                break
        
        if not approval_msg:
            self.log("No unused approval notice found - buttons may have been used already")
            return
        
        self.test("Found approval notice with buttons", True)
        
        # Try to press a button
        button = approval_msg["buttons"][0]  # "Allow once"
        status, resp = self.api_call("POST", "/chat/actions", token, {
            "action_id": button["id"],
            "msg_id": approval_msg["msg_id"],
            "label": button["label"]
        })
        
        self.test("Press approval button", status == 200, f"Status: {status}")
        
        if status == 200:
            self.test("Button press returns text", resp.get("text") is not None)
            self.test("Button press returns user_message", resp.get("user_message") is not None)
            self.test("Button press returns message", resp.get("message") is not None)
            
            # Try pressing again - should get 409
            status2, resp2 = self.api_call("POST", "/chat/actions", token, {
                "action_id": button["id"],
                "msg_id": approval_msg["msg_id"],
                "label": button["label"]
            })
            self.test("Second button press returns 409", status2 == 409,
                     f"Expected 409, got {status2}")
    
    def run_all_tests(self):
        """Run all test suites"""
        self.log("\n" + "="*60)
        self.log("KONNTO AI Backend API Testing")
        self.log("="*60)
        
        self.test_owner_access()
        self.test_priya_access()
        self.test_supplier_access()
        self.test_chat_action_buttons()
        
        # Summary
        self.log("\n" + "="*60)
        self.log(f"TESTS COMPLETED: {self.tests_passed}/{self.tests_run} passed")
        self.log("="*60)
        
        if self.issues:
            self.log("\n❌ ISSUES FOUND:")
            for issue in self.issues:
                self.log(f"  - {issue}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = KONNTOTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
