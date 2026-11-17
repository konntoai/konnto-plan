"""K-BRAIN master-prompt check: drafts-first, confirm, memory, scores. Usage: python kbrain_master.py <email> [msg ...]"""
import sys, json, subprocess
import requests

BASE = open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0].strip() + '/api'
email = sys.argv[1]
tok = subprocess.check_output(['python', '/app/tests/clerk_token.py', email, 'Riya']).decode().strip()
H = {'Authorization': f'Bearer {tok}'}
me = requests.get(f'{BASE}/me', headers=H).json()
if me.get('needs_onboarding'):
    requests.post(f'{BASE}/onboarding', headers=H, json={'whatsapp': '+919812345671', 'consent': False, 'timezone': 'Asia/Kolkata', 'name': 'Riya Kapoor'})


def chat(text, confirm=True):
    out, cards = [], []
    with requests.post(f'{BASE}/chat/stream', headers=H, json={'text': text}, stream=True, timeout=240) as r:
        for line in r.iter_lines():
            if line and line.startswith(b'data: '):
                ev = json.loads(line[6:])
                if ev['type'] == 'delta':
                    out.append(ev['text'])
                elif ev['type'] == 'done':
                    cards = ev['message'].get('cards', [])
    print('\n>>>', text, '\n' + ''.join(out)[:2500])
    for c in cards:
        print('   CARD', c['type'], c['status'], json.dumps(c['data'])[:250])
        if confirm and c['status'] == 'draft':
            r = requests.post(f"{BASE}/chat/cards/{c['card_id']}/confirm", headers=H, json={})
            print('   CONFIRM ->', r.status_code, (r.json().get('card') or r.json()).get('status', r.json()))


for q in sys.argv[2:]:
    chat(q)
