"""Backend API tests for KONNTO AI Phase 1 MVP"""
import requests
import sys
import json
from datetime import datetime

BASE_URL = "https://konnto-plan--87psd4r7.preview.emergentagent.com/api"

class KONNTOTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.org_id = None
        self.member_id = None
        self.item_id = None
        self.approval_id = None
        self.thread_id = None
        self.member_to_invite_id = None
        self.fact_id = None
        self.rule_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        req_headers = {'Content-Type': 'application/json'}
        if self.token:
            req_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            req_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=req_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=req_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=req_headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=req_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=req_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"   Response: {response.text[:200]}")
                except:
                    pass
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def set_token(self, token):
        """Set the auth token"""
        self.token = token
        print(f"✅ Token set")

    def test_root(self):
        """Test root endpoint"""
        success, response = self.run_test(
            "Root endpoint",
            "GET",
            "/",
            200
        )
        return success

    def test_onboarding(self, whatsapp, name):
        """Test onboarding and seed"""
        success, response = self.run_test(
            "Onboarding + Demo Seed",
            "POST",
            "/onboarding",
            200,
            data={
                "whatsapp": whatsapp,
                "consent": True,
                "name": name
            }
        )
        if success and response.get('org_id'):
            self.org_id = response['org_id']
            print(f"   Org created: {self.org_id}")
        return success

    def test_me(self):
        """Test GET /me"""
        success, response = self.run_test(
            "GET /me",
            "GET",
            "/me",
            200
        )
        if success:
            print(f"   User: {response.get('user', {}).get('name')}")
            print(f"   Org: {response.get('org', {}).get('name')}")
            print(f"   Member: {response.get('member', {}).get('name')}")
            print(f"   Needs onboarding: {response.get('needs_onboarding')}")
            print(f"   Pending approvals: {response.get('pending_approvals')}")
            print(f"   WhatsApp connected: {response.get('whatsapp_connected')}")
            if response.get('member'):
                self.member_id = response['member']['member_id']
        return success

    def test_dashboard(self):
        """Test GET /dashboard"""
        success, response = self.run_test(
            "GET /dashboard",
            "GET",
            "/dashboard",
            200
        )
        if success:
            counts = response.get('counts', {})
            print(f"   Overdue: {counts.get('overdue')}")
            print(f"   Due today: {counts.get('due_today')}")
            print(f"   Stuck: {counts.get('stuck')}")
            print(f"   Done this week: {counts.get('done_week')}")
            print(f"   Approvals: {counts.get('approvals')}")
            print(f"   Team: {counts.get('team')}")
            print(f"   Brief present: {bool(response.get('brief'))}")
        return success

    def test_items_list(self, state="all"):
        """Test GET /items with filters"""
        success, response = self.run_test(
            f"GET /items?state={state}",
            "GET",
            f"/items?state={state}",
            200
        )
        if success:
            items = response.get('items', [])
            print(f"   Found {len(items)} items")
            if items and not self.item_id:
                self.item_id = items[0]['item_id']
                print(f"   First item: {items[0].get('title')}")
        return success

    def test_members_list(self):
        """Test GET /members"""
        success, response = self.run_test(
            "GET /members",
            "GET",
            "/members",
            200
        )
        if success:
            members = response.get('members', [])
            print(f"   Found {len(members)} members")
            for m in members:
                print(f"   - {m.get('name')} ({m.get('member_type')})")
        return success

    def test_invite_member(self):
        """Test POST /members (invite)"""
        success, response = self.run_test(
            "POST /members (invite)",
            "POST",
            "/members",
            200,
            data={
                "name": "TEST_Automation User",
                "job": "Test Engineer",
                "member_type": "team",
                "phone": "+919999999999"
            }
        )
        if success:
            member = response.get('member', {})
            links = response.get('links', {})
            self.member_to_invite_id = member.get('member_id')
            print(f"   Invited: {member.get('name')}")
            print(f"   Invite URL: {links.get('invite_url', 'N/A')[:50]}...")
            print(f"   Invite code: {links.get('invite_code')}")
        return success

    def test_threads_list(self):
        """Test GET /threads"""
        success, response = self.run_test(
            "GET /threads",
            "GET",
            "/threads",
            200
        )
        if success:
            threads = response.get('threads', [])
            print(f"   Found {len(threads)} threads")
            if threads:
                self.thread_id = threads[0]['thread_id']
                print(f"   First thread: {threads[0].get('title')}")
        return success

    def test_thread_messages(self):
        """Test GET /threads/{id}/messages"""
        if not self.thread_id:
            print("⚠️  Skipping - no thread_id")
            return False
        
        success, response = self.run_test(
            f"GET /threads/{self.thread_id}/messages",
            "GET",
            f"/threads/{self.thread_id}/messages",
            200
        )
        if success:
            messages = response.get('messages', [])
            people = response.get('people', [])
            print(f"   Found {len(messages)} messages")
            print(f"   People in thread: {len(people)}")
        return success

    def test_post_thread_message(self):
        """Test POST /threads/{id}/messages"""
        if not self.thread_id:
            print("⚠️  Skipping - no thread_id")
            return False
        
        success, response = self.run_test(
            f"POST /threads/{self.thread_id}/messages",
            "POST",
            f"/threads/{self.thread_id}/messages",
            200,
            data={"text": "TEST_Automation message - please ignore"}
        )
        if success:
            print(f"   Message sent: {response.get('msg_id')}")
        return success

    def test_approvals_list(self):
        """Test GET /approvals?status=pending"""
        success, response = self.run_test(
            "GET /approvals?status=pending",
            "GET",
            "/approvals?status=pending",
            200
        )
        if success:
            approvals = response.get('approvals', [])
            print(f"   Found {len(approvals)} pending approvals")
            if approvals:
                self.approval_id = approvals[0]['approval_id']
                print(f"   First approval: {approvals[0].get('title')}")
        return success

    def test_decide_approval(self):
        """Test POST /approvals/{id}/decide"""
        if not self.approval_id:
            print("⚠️  Skipping - no approval_id")
            return False
        
        success, response = self.run_test(
            f"POST /approvals/{self.approval_id}/decide",
            "POST",
            f"/approvals/{self.approval_id}/decide",
            200,
            data={"decision": "once", "note": "TEST_Automation approval"}
        )
        if success:
            print(f"   Decision: {response.get('approval', {}).get('status')}")
        return success

    def test_undo_approval(self):
        """Test POST /approvals/{id}/undo"""
        if not self.approval_id:
            print("⚠️  Skipping - no approval_id")
            return False
        
        success, response = self.run_test(
            f"POST /approvals/{self.approval_id}/undo",
            "POST",
            f"/approvals/{self.approval_id}/undo",
            200
        )
        if success:
            print(f"   Undone: {response.get('approval', {}).get('status')}")
        return success

    def test_knowledge_list(self):
        """Test GET /knowledge"""
        success, response = self.run_test(
            "GET /knowledge",
            "GET",
            "/knowledge",
            200
        )
        if success:
            facts = response.get('facts', [])
            rules = response.get('rules', [])
            print(f"   Facts: {len(facts)}")
            print(f"   Rules: {len(rules)}")
            print(f"   Documents: {response.get('documents', 0)}")
            print(f"   People: {response.get('people', 0)}")
        return success

    def test_create_fact(self):
        """Test POST /knowledge"""
        success, response = self.run_test(
            "POST /knowledge",
            "POST",
            "/knowledge",
            200,
            data={"text": "TEST_Automation fact - please ignore"}
        )
        if success:
            self.fact_id = response.get('fact_id')
            print(f"   Fact created: {self.fact_id}")
        return success

    def test_delete_fact(self):
        """Test DELETE /knowledge/{id}"""
        if not self.fact_id:
            print("⚠️  Skipping - no fact_id")
            return False
        
        success, response = self.run_test(
            f"DELETE /knowledge/{self.fact_id}",
            "DELETE",
            f"/knowledge/{self.fact_id}",
            200
        )
        if success:
            print(f"   Fact deleted (soft)")
        return success

    def test_rules_list(self):
        """Test GET /rules"""
        success, response = self.run_test(
            "GET /rules",
            "GET",
            "/rules",
            200
        )
        if success:
            rules = response.get('rules', [])
            print(f"   Found {len(rules)} rules")
        return success

    def test_privacy_summary(self):
        """Test GET /privacy/summary"""
        success, response = self.run_test(
            "GET /privacy/summary",
            "GET",
            "/privacy/summary",
            200
        )
        if success:
            counts = response.get('counts', {})
            print(f"   KONNTO messages: {counts.get('konnto_messages')}")
            print(f"   Items created: {counts.get('items_created')}")
        return success

    def test_privacy_export(self):
        """Test GET /privacy/export"""
        success, response = self.run_test(
            "GET /privacy/export",
            "GET",
            "/privacy/export",
            200
        )
        if success:
            print(f"   Export data received")
        return success

    def test_delete_invited_member(self):
        """Test DELETE /members/{id} (cleanup)"""
        if not self.member_to_invite_id:
            print("⚠️  Skipping - no member_to_invite_id")
            return False
        
        success, response = self.run_test(
            f"DELETE /members/{self.member_to_invite_id}",
            "DELETE",
            f"/members/{self.member_to_invite_id}",
            200
        )
        if success:
            print(f"   Member removed (soft)")
        return success


def main():
    """Run all backend tests"""
    print("=" * 60)
    print("KONNTO AI Backend API Tests")
    print("=" * 60)
    
    # Get token from command line
    if len(sys.argv) < 2:
        print("❌ Usage: python backend_test.py <clerk_jwt_token>")
        print("   Generate token: python /app/tests/clerk_token.py test.konnto@gmail.com TestUser token")
        return 1
    
    token = sys.argv[1]
    tester = KONNTOTester()
    tester.set_token(token)
    
    # Run tests in order
    print("\n" + "=" * 60)
    print("Phase 1: Basic Endpoints")
    print("=" * 60)
    tester.test_root()
    
    print("\n" + "=" * 60)
    print("Phase 2: Onboarding & User")
    print("=" * 60)
    tester.test_onboarding("+919876543210", "TEST_Automation User")
    tester.test_me()
    
    print("\n" + "=" * 60)
    print("Phase 3: Dashboard & Work Items")
    print("=" * 60)
    tester.test_dashboard()
    tester.test_items_list("all")
    tester.test_items_list("overdue")
    tester.test_items_list("due")
    tester.test_items_list("stuck")
    tester.test_items_list("done")
    
    print("\n" + "=" * 60)
    print("Phase 4: Team & Threads")
    print("=" * 60)
    tester.test_members_list()
    tester.test_invite_member()
    tester.test_threads_list()
    tester.test_thread_messages()
    tester.test_post_thread_message()
    
    print("\n" + "=" * 60)
    print("Phase 5: Approvals")
    print("=" * 60)
    tester.test_approvals_list()
    tester.test_decide_approval()
    tester.test_undo_approval()
    
    print("\n" + "=" * 60)
    print("Phase 6: Knowledge & Rules")
    print("=" * 60)
    tester.test_knowledge_list()
    tester.test_create_fact()
    tester.test_delete_fact()
    tester.test_rules_list()
    
    print("\n" + "=" * 60)
    print("Phase 7: Privacy")
    print("=" * 60)
    tester.test_privacy_summary()
    tester.test_privacy_export()
    
    print("\n" + "=" * 60)
    print("Phase 8: Cleanup")
    print("=" * 60)
    tester.test_delete_invited_member()
    
    # Print results
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"📈 Success rate: {success_rate:.1f}%")
    
    return 0 if tester.tests_passed == tester.tests_run else 1


if __name__ == "__main__":
    sys.exit(main())
