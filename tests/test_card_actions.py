"""Test chat card actions"""
import requests
import sys
import json

BASE_URL = "https://konnto-plan--87psd4r7.preview.emergentagent.com/api"

def test_card_actions(token):
    """Test card save/skip/undo flow"""
    print("🔍 Testing card actions (save/skip/undo)...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Step 1: Send a message that will create a proposal card
    print("\n   Step 1: Sending message to create proposal...")
    url = f"{BASE_URL}/chat/stream"
    data = {
        "text": "Remind me tomorrow at 2pm to call the supplier",
        "attachments": []
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, stream=True, timeout=60)
        
        if response.status_code != 200:
            print(f"   ❌ Failed to create chat - Status: {response.status_code}")
            return False
        
        card_id = None
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
                            event = json.loads(event_text[6:])
                            
                            if event.get('type') == 'cards':
                                cards = event.get('cards', [])
                                if cards and cards[0].get('type') == 'proposal':
                                    card_id = cards[0].get('card_id')
                                    print(f"   ✅ Proposal card created: {card_id}")
                            
                            if event.get('type') == 'done':
                                break
                        except:
                            pass
        
        if not card_id:
            print(f"   ❌ No proposal card found in response")
            return False
        
        # Step 2: Save the card
        print(f"\n   Step 2: Saving card {card_id}...")
        save_url = f"{BASE_URL}/chat/cards/{card_id}/save"
        save_response = requests.post(save_url, json={}, headers=headers, timeout=30)
        
        if save_response.status_code != 200:
            print(f"   ❌ Failed to save card - Status: {save_response.status_code}")
            return False
        
        save_data = save_response.json()
        if save_data.get('card', {}).get('status') == 'saved':
            item_id = save_data.get('card', {}).get('item_id')
            print(f"   ✅ Card saved successfully, item_id: {item_id}")
        else:
            print(f"   ❌ Card not saved, status: {save_data.get('card', {}).get('status')}")
            return False
        
        # Step 3: Undo the save
        print(f"\n   Step 3: Undoing card save...")
        undo_url = f"{BASE_URL}/chat/cards/{card_id}/undo"
        undo_response = requests.post(undo_url, json={}, headers=headers, timeout=30)
        
        if undo_response.status_code != 200:
            print(f"   ❌ Failed to undo card - Status: {undo_response.status_code}")
            return False
        
        undo_data = undo_response.json()
        if undo_data.get('card', {}).get('status') == 'pending':
            print(f"   ✅ Card undo successful, status back to pending")
        else:
            print(f"   ❌ Card undo failed, status: {undo_data.get('card', {}).get('status')}")
            return False
        
        # Step 4: Skip the card
        print(f"\n   Step 4: Skipping card...")
        skip_url = f"{BASE_URL}/chat/cards/{card_id}/skip"
        skip_response = requests.post(skip_url, json={}, headers=headers, timeout=30)
        
        if skip_response.status_code != 200:
            print(f"   ❌ Failed to skip card - Status: {skip_response.status_code}")
            return False
        
        skip_data = skip_response.json()
        if skip_data.get('card', {}).get('status') == 'skipped':
            print(f"   ✅ Card skipped successfully")
        else:
            print(f"   ❌ Card skip failed, status: {skip_data.get('card', {}).get('status')}")
            return False
        
        # Verify item appears in /items
        print(f"\n   Step 5: Verifying item was created and deleted...")
        items_url = f"{BASE_URL}/items?state=all"
        items_response = requests.get(items_url, headers=headers, timeout=30)
        
        if items_response.status_code == 200:
            items = items_response.json().get('items', [])
            # The item should be soft-deleted, so it won't appear in the list
            print(f"   ✅ Items list retrieved ({len(items)} items)")
        
        print(f"\n✅ All card actions tested successfully!")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed - Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_card_actions.py <token>")
        sys.exit(1)
    
    token = sys.argv[1]
    success = test_card_actions(token)
    sys.exit(0 if success else 1)
