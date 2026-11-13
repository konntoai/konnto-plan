"""Test chat streaming endpoint"""
import requests
import sys

BASE_URL = "https://konnto-plan--87psd4r7.preview.emergentagent.com/api"

def test_chat_stream(token):
    """Test POST /chat/stream"""
    print("🔍 Testing POST /chat/stream...")
    
    url = f"{BASE_URL}/chat/stream"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    data = {
        "text": "What tasks are overdue?",
        "attachments": []
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, stream=True, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ Failed - Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
        
        print(f"✅ Stream started - Status: {response.status_code}")
        
        events = []
        buffer = ""
        
        for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
            if chunk:
                buffer += chunk
                while "\n\n" in buffer:
                    idx = buffer.index("\n\n")
                    event_text = buffer[:idx]
                    buffer = buffer[idx+2:]
                    
                    if event_text.startswith("data: "):
                        try:
                            import json
                            event = json.loads(event_text[6:])
                            events.append(event)
                            print(f"   Event: {event.get('type')}")
                            
                            if event.get('type') == 'done':
                                print(f"   ✅ Stream completed")
                                print(f"   Total events: {len(events)}")
                                
                                # Verify event sequence
                                types = [e.get('type') for e in events]
                                if 'user' in types and 'done' in types:
                                    print(f"   ✅ Event sequence valid: {' -> '.join(types)}")
                                    
                                    # Check if done event has message
                                    done_event = events[-1]
                                    if done_event.get('message'):
                                        print(f"   ✅ Done event contains final message")
                                        return True
                                    else:
                                        print(f"   ❌ Done event missing message")
                                        return False
                                else:
                                    print(f"   ❌ Invalid event sequence: {types}")
                                    return False
                        except Exception as e:
                            print(f"   ⚠️  Parse error: {e}")
        
        print(f"   ❌ Stream ended without 'done' event")
        return False
        
    except Exception as e:
        print(f"❌ Failed - Error: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_chat_stream.py <token>")
        sys.exit(1)
    
    token = sys.argv[1]
    success = test_chat_stream(token)
    sys.exit(0 if success else 1)
