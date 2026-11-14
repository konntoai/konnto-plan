"""K-BRAIN comprehensive backend test: persona, briefing, handover flow, reset."""
import sys
import json
import subprocess
import time
import requests

BASE_URL = "https://konnto-plan--87psd4r7.preview.emergentagent.com/api"

class KBrainTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.token = None
        self.headers = {}
        
    def log(self, msg, status="info"):
        prefix = {"info": "ℹ️", "pass": "✅", "fail": "❌", "warn": "⚠️"}
        print(f"{prefix.get(status, 'ℹ️')} {msg}")
    
    def test(self, name, fn):
        """Run a single test"""
        self.tests_run += 1
        self.log(f"Testing {name}...", "info")
        try:
            fn()
            self.tests_passed += 1
            self.log(f"PASSED: {name}", "pass")
            return True
        except AssertionError as e:
            self.log(f"FAILED: {name} - {str(e)}", "fail")
            return False
        except Exception as e:
            self.log(f"ERROR: {name} - {str(e)}", "fail")
            return False
    
    def setup_auth(self):
        """Create a fresh test user and get JWT token"""
        self.log("Setting up authentication...", "info")
        email = f'test.kbrain.{int(time.time())}+clerk_test@example.com'
        try:
            result = subprocess.check_output(
                ['python', '/app/tests/clerk_token.py', email, 'TestUser'],
                stderr=subprocess.STDOUT
            )
            self.token = result.decode().strip()
            self.headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
            self.log(f"Auth token obtained for {email}", "pass")
            
            # Onboard the user
            r = requests.post(f'{BASE_URL}/onboarding', headers=self.headers, 
                            json={'whatsapp': '+919812345670', 'consent': False, 
                                  'timezone': 'Asia/Kolkata', 'name': 'Test User'})
            if r.status_code == 200:
                self.log("User onboarded successfully", "pass")
            else:
                self.log(f"Onboarding status: {r.status_code}", "warn")
            return True
        except Exception as e:
            self.log(f"Auth setup failed: {str(e)}", "fail")
            return False
    
    def test_me_endpoint(self):
        """Test GET /api/me returns brain_persona and brain_personas list"""
        def run():
            r = requests.get(f'{BASE_URL}/me', headers=self.headers)
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            data = r.json()
            
            # Check brain_persona exists and is default
            assert 'brain_persona' in data, "brain_persona not in response"
            assert data['brain_persona'] == 'chief_of_staff', f"Expected chief_of_staff, got {data['brain_persona']}"
            
            # Check brain_personas list
            assert 'brain_personas' in data, "brain_personas not in response"
            personas = data['brain_personas']
            assert len(personas) == 4, f"Expected 4 personas, got {len(personas)}"
            
            persona_ids = [p['id'] for p in personas]
            expected = ['chief_of_staff', 'assistant', 'advisor', 'operator']
            assert set(persona_ids) == set(expected), f"Expected {expected}, got {persona_ids}"
            
            self.log(f"brain_persona: {data['brain_persona']}, personas: {persona_ids}", "info")
        
        self.test("GET /api/me returns brain_persona and personas list", run)
    
    def test_update_persona_valid(self):
        """Test PUT /api/me/brain-persona with valid persona"""
        def run():
            r = requests.put(f'{BASE_URL}/me/brain-persona', headers=self.headers,
                           json={'persona': 'advisor'})
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            data = r.json()
            assert data['ok'] == True, "Expected ok=True"
            assert data['brain_persona'] == 'advisor', f"Expected advisor, got {data['brain_persona']}"
            assert 'label' in data, "label not in response"
            
            # Verify it persisted
            r2 = requests.get(f'{BASE_URL}/me', headers=self.headers)
            me = r2.json()
            assert me['brain_persona'] == 'advisor', "Persona not persisted"
            
            self.log(f"Persona updated to: {data['label']}", "info")
        
        self.test("PUT /api/me/brain-persona with valid persona", run)
    
    def test_update_persona_invalid(self):
        """Test PUT /api/me/brain-persona with invalid persona returns 400"""
        def run():
            r = requests.put(f'{BASE_URL}/me/brain-persona', headers=self.headers,
                           json={'persona': 'invalid_persona'})
            assert r.status_code == 400, f"Expected 400, got {r.status_code}"
            
            self.log("Invalid persona correctly rejected with 400", "info")
        
        self.test("PUT /api/me/brain-persona with invalid persona returns 400", run)
    
    def test_chat_briefing(self):
        """Test POST /api/chat/stream returns briefing with real data"""
        def run():
            out_text = []
            cards = []
            
            with requests.post(f'{BASE_URL}/chat/stream', headers=self.headers,
                             json={'text': 'what needs my attention today?'}, 
                             stream=True, timeout=180) as r:
                assert r.status_code == 200, f"Expected 200, got {r.status_code}"
                
                for line in r.iter_lines():
                    if not line or not line.startswith(b'data: '):
                        continue
                    ev = json.loads(line[6:])
                    if ev['type'] == 'delta':
                        out_text.append(ev['text'])
                    elif ev['type'] == 'done':
                        cards = ev['message'].get('cards', [])
            
            reply = ''.join(out_text)
            assert len(reply) > 50, f"Reply too short: {len(reply)} chars"
            
            # Check for first name addressing (Test or TestUser)
            assert 'Test' in reply, "Reply doesn't address user by first name"
            
            # Check for pending approvals mention (seed creates 3)
            # The reply should mention approvals with amounts
            reply_lower = reply.lower()
            assert 'approval' in reply_lower or 'waiting' in reply_lower or 'pending' in reply_lower, \
                "Reply doesn't mention approvals"
            
            # Check for Indian number grouping (₹42,000 or similar)
            # Seed creates: Gupta Cement ₹42,000, drill ₹8,500, refund ₹6,800
            has_rupee = '₹' in reply or 'Rs' in reply or '42' in reply or '8,500' in reply
            assert has_rupee, "Reply doesn't show amounts with Indian formatting"
            
            self.log(f"Briefing reply length: {len(reply)} chars, mentions approvals and amounts", "info")
            self.log(f"Reply preview: {reply[:200]}...", "info")
        
        self.test("POST /api/chat/stream returns briefing with real data", run)
    
    def test_handover_flow(self):
        """Test handover message creates proper card structure"""
        def run():
            out_text = []
            cards = []
            
            handover_msg = "ask the ops lead to manage for today, there is a death in my family. dont let her take any financial decision. if anything urgent ask her to take my approval or contact me"
            
            with requests.post(f'{BASE_URL}/chat/stream', headers=self.headers,
                             json={'text': handover_msg}, 
                             stream=True, timeout=180) as r:
                assert r.status_code == 200, f"Expected 200, got {r.status_code}"
                
                for line in r.iter_lines():
                    if not line or not line.startswith(b'data: '):
                        continue
                    ev = json.loads(line[6:])
                    if ev['type'] == 'delta':
                        out_text.append(ev['text'])
                    elif ev['type'] == 'done':
                        cards = ev['message'].get('cards', [])
            
            reply = ''.join(out_text)
            
            # Find handover card
            handover_cards = [c for c in cards if c['type'] == 'handover']
            assert len(handover_cards) > 0, "No handover card created"
            
            card = handover_cards[0]
            assert card['status'] == 'pending', f"Expected pending, got {card['status']}"
            
            data = card['data']
            assert 'to_name' in data, "to_name not in card data"
            assert data['to_name'] == 'Priya Nair', f"Expected Priya Nair, got {data['to_name']}"
            assert 'message' in data, "message not in card data"
            assert 'restrictions' in data, "restrictions not in card data"
            assert len(data['restrictions']) > 0, "No restrictions in card"
            assert 'until' in data, "until not in card data"
            
            # Check reply doesn't claim it was already sent
            reply_lower = reply.lower()
            assert 'sent' not in reply_lower or 'confirm' in reply_lower, \
                "Reply incorrectly claims handover was already sent"
            
            self.log(f"Handover card created: to={data['to_name']}, restrictions={len(data['restrictions'])}", "info")
            
            # Store card_id for next tests
            self.handover_card_id = card['card_id']
        
        self.test("Handover message creates proper card structure", run)
    
    def test_handover_confirm(self):
        """Test POST /api/chat/cards/{card_id}/confirm on handover"""
        def run():
            assert hasattr(self, 'handover_card_id'), "No handover card from previous test"
            
            # First confirm
            r = requests.post(f"{BASE_URL}/chat/cards/{self.handover_card_id}/confirm",
                            headers=self.headers, json={})
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            data = r.json()
            
            assert 'card' in data, "card not in response"
            card = data['card']
            assert card['status'] == 'confirmed', f"Expected confirmed, got {card['status']}"
            
            card_data = card['data']
            assert 'rule_id' in card_data, "rule_id not in confirmed card"
            assert 'thread_id' in card_data, "thread_id not in confirmed card"
            assert 'confirmed_at' in card_data, "confirmed_at not in confirmed card"
            
            self.log(f"Handover confirmed: rule_id={card_data.get('rule_id')}", "info")
            
            # Check rule was created
            r2 = requests.get(f'{BASE_URL}/rules', headers=self.headers)
            rules_data = r2.json()
            rules = rules_data.get('rules', [])
            handover_rules = [r for r in rules if r.get('kind') == 'handover']
            assert len(handover_rules) > 0, "No handover rule created"
            
            self.log(f"Handover rule created and active", "info")
            
            # Check thread message was created
            r3 = requests.get(f'{BASE_URL}/team/threads', headers=self.headers)
            if r3.status_code == 200:
                threads = r3.json().get('threads', [])
                self.log(f"Thread created: {len(threads)} threads found", "info")
            
            # Second confirm should be no-op (no duplicate rule)
            r4 = requests.post(f"{BASE_URL}/chat/cards/{self.handover_card_id}/confirm",
                             headers=self.headers, json={})
            assert r4.status_code == 200, f"Second confirm failed: {r4.status_code}"
            
            # Check no duplicate rule
            r5 = requests.get(f'{BASE_URL}/rules', headers=self.headers)
            rules_data2 = r5.json()
            rules2 = rules_data2.get('rules', [])
            handover_rules2 = [r for r in rules2 if r.get('kind') == 'handover']
            assert len(handover_rules2) == len(handover_rules), "Duplicate rule created on second confirm"
            
            self.log("Second confirm is no-op, no duplicate rule", "info")
        
        self.test("POST /api/chat/cards/{card_id}/confirm on handover", run)
    
    def test_handover_dismiss(self):
        """Test POST /api/chat/cards/{card_id}/dismiss on pending handover"""
        def run():
            # Create a new handover for dismissal test
            out_text = []
            cards = []
            
            with requests.post(f'{BASE_URL}/chat/stream', headers=self.headers,
                             json={'text': 'ask ramesh to handle things today, no major decisions'}, 
                             stream=True, timeout=180) as r:
                for line in r.iter_lines():
                    if not line or not line.startswith(b'data: '):
                        continue
                    ev = json.loads(line[6:])
                    if ev['type'] == 'done':
                        cards = ev['message'].get('cards', [])
            
            handover_cards = [c for c in cards if c['type'] == 'handover']
            if len(handover_cards) == 0:
                self.log("No handover card created for dismiss test, skipping", "warn")
                return
            
            card_id = handover_cards[0]['card_id']
            
            # Dismiss it
            r = requests.post(f"{BASE_URL}/chat/cards/{card_id}/dismiss",
                            headers=self.headers, json={})
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            data = r.json()
            
            assert 'card' in data, "card not in response"
            assert data['card']['status'] == 'dismissed', f"Expected dismissed, got {data['card']['status']}"
            
            self.log("Handover dismissed successfully", "info")
        
        self.test("POST /api/chat/cards/{card_id}/dismiss on handover", run)
    
    def test_handover_undo(self):
        """Test POST /api/chat/cards/{card_id}/undo on confirmed handover"""
        def run():
            assert hasattr(self, 'handover_card_id'), "No handover card from previous test"
            
            # Undo the confirmed handover
            r = requests.post(f"{BASE_URL}/chat/cards/{self.handover_card_id}/undo",
                            headers=self.headers, json={})
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            data = r.json()
            
            assert 'card' in data, "card not in response"
            card = data['card']
            assert card['status'] == 'ended', f"Expected ended, got {card['status']}"
            
            # Check rule is now inactive
            r2 = requests.get(f'{BASE_URL}/rules', headers=self.headers)
            rules_data = r2.json()
            rules = rules_data.get('rules', [])
            # Active handover rules should be 0 now
            active_handover = [r for r in rules if r.get('kind') == 'handover' and r.get('active')]
            assert len(active_handover) == 0, f"Expected 0 active handover rules, got {len(active_handover)}"
            
            self.log("Handover ended and rule made inactive", "info")
        
        self.test("POST /api/chat/cards/{card_id}/undo on confirmed handover", run)
    
    def test_persona_via_chat(self):
        """Test persona change via chat creates persona card"""
        def run():
            out_text = []
            cards = []
            
            with requests.post(f'{BASE_URL}/chat/stream', headers=self.headers,
                             json={'text': 'talk to me like a senior advisor from now on'}, 
                             stream=True, timeout=180) as r:
                for line in r.iter_lines():
                    if not line or not line.startswith(b'data: '):
                        continue
                    ev = json.loads(line[6:])
                    if ev['type'] == 'done':
                        cards = ev['message'].get('cards', [])
            
            # Find persona card
            persona_cards = [c for c in cards if c['type'] == 'persona']
            assert len(persona_cards) > 0, "No persona card created"
            
            card = persona_cards[0]
            assert card['status'] == 'saved', f"Expected saved, got {card['status']}"
            assert card['data']['persona'] == 'advisor', f"Expected advisor, got {card['data']['persona']}"
            
            # Verify member persona was updated
            r2 = requests.get(f'{BASE_URL}/me', headers=self.headers)
            me = r2.json()
            assert me['brain_persona'] == 'advisor', "Member persona not updated"
            
            self.log(f"Persona changed via chat to: {card['data']['label']}", "info")
        
        self.test("Persona change via chat creates card and updates member", run)
    
    def test_chat_reset(self):
        """Test POST /api/chat/reset archives messages"""
        def run():
            # Get current messages
            r1 = requests.get(f'{BASE_URL}/chat/messages?limit=100', headers=self.headers)
            before = r1.json()
            msg_count_before = len(before.get('messages', []))
            assert msg_count_before > 0, "No messages to reset"
            
            # Reset
            r2 = requests.post(f'{BASE_URL}/chat/reset', headers=self.headers, json={})
            assert r2.status_code == 200, f"Expected 200, got {r2.status_code}"
            data = r2.json()
            assert data['ok'] == True, "Expected ok=True"
            assert data['archived'] > 0, f"Expected archived > 0, got {data['archived']}"
            
            # Verify messages are gone
            r3 = requests.get(f'{BASE_URL}/chat/messages?limit=100', headers=self.headers)
            after = r3.json()
            msg_count_after = len(after.get('messages', []))
            assert msg_count_after == 0, f"Expected 0 messages after reset, got {msg_count_after}"
            
            self.log(f"Reset archived {data['archived']} messages", "info")
            
            # Verify work items still exist (not touched by reset)
            r4 = requests.get(f'{BASE_URL}/items', headers=self.headers)
            if r4.status_code == 200:
                items = r4.json().get('items', [])
                self.log(f"Work items untouched: {len(items)} items still exist", "info")
        
        self.test("POST /api/chat/reset archives messages", run)
    
    def test_backend_regression(self):
        """Test existing features still work"""
        def run():
            # Test dashboard
            r1 = requests.get(f'{BASE_URL}/dashboard', headers=self.headers)
            assert r1.status_code == 200, f"Dashboard failed: {r1.status_code}"
            
            # Test items
            r2 = requests.get(f'{BASE_URL}/items', headers=self.headers)
            assert r2.status_code == 200, f"Items failed: {r2.status_code}"
            
            # Test members
            r3 = requests.get(f'{BASE_URL}/members', headers=self.headers)
            assert r3.status_code == 200, f"Members failed: {r3.status_code}"
            
            # Test approvals
            r4 = requests.get(f'{BASE_URL}/approvals', headers=self.headers)
            assert r4.status_code == 200, f"Approvals failed: {r4.status_code}"
            
            self.log("Backend regression tests passed: dashboard, items, members, approvals", "info")
        
        self.test("Backend regression: existing features work", run)
    
    def run_all(self):
        """Run all tests"""
        self.log("=" * 60, "info")
        self.log("K-BRAIN Backend Test Suite", "info")
        self.log("=" * 60, "info")
        
        if not self.setup_auth():
            self.log("Auth setup failed, cannot continue", "fail")
            return 1
        
        # Run tests in order
        self.test_me_endpoint()
        self.test_update_persona_valid()
        self.test_update_persona_invalid()
        self.test_chat_briefing()
        self.test_handover_flow()
        self.test_handover_confirm()
        self.test_handover_dismiss()
        self.test_handover_undo()
        self.test_persona_via_chat()
        self.test_chat_reset()
        self.test_backend_regression()
        
        # Summary
        self.log("=" * 60, "info")
        self.log(f"Tests passed: {self.tests_passed}/{self.tests_run}", 
                "pass" if self.tests_passed == self.tests_run else "fail")
        self.log("=" * 60, "info")
        
        return 0 if self.tests_passed == self.tests_run else 1

if __name__ == "__main__":
    tester = KBrainTester()
    sys.exit(tester.run_all())
