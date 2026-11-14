"""K-BRAIN conversational check: briefing, urgency, handover card + confirm, persona."""
import sys, json, subprocess, time
import requests

BASE = open('/app/frontend/.env').read().split('REACT_APP_BACKEND_URL=')[1].split()[0].strip() + '/api'
email = sys.argv[1] if len(sys.argv) > 1 else f'riya.kb{int(time.time())}+clerk_test@example.com'
tok = subprocess.check_output(['python', '/app/tests/clerk_token.py', email, 'Riya']).decode().strip()
H = {'Authorization': f'Bearer {tok}'}

me = requests.get(f'{BASE}/me', headers=H).json()
if me.get('needs_onboarding'):
    r = requests.post(f'{BASE}/onboarding', headers=H, json={'whatsapp': '+919812345670', 'consent': False, 'timezone': 'Asia/Kolkata', 'name': 'Riya Kapoor'})
    print('onboard', r.status_code)
    me = requests.get(f'{BASE}/me', headers=H).json()
print('persona', me.get('brain_persona'), [p['id'] for p in me.get('brain_personas', [])])


def chat(text):
    out, cards = [], []
    with requests.post(f'{BASE}/chat/stream', headers=H, json={'text': text}, stream=True, timeout=180) as r:
        for line in r.iter_lines():
            if not line or not line.startswith(b'data: '):
                continue
            ev = json.loads(line[6:])
            if ev['type'] == 'delta':
                out.append(ev['text'])
            elif ev['type'] == 'done':
                cards = ev['message'].get('cards', [])
    print('\n>>>', text, '\n' + ''.join(out))
    for c in cards:
        print('   CARD', c['type'], c['status'], json.dumps(c['data'])[:400])
    return cards


for q in sys.argv[2:] or ['what needs my attention today?', 'what is really urgent for today?',
                          'ask the ops lead to manage for today, there is a death in my family really cant handle things. Also dont let her take any financial decision. If anything urgent comes up ask her to take my approval or contact me']:
    cards = chat(q)
    for c in cards:
        if c['type'] == 'handover':
            r = requests.post(f"{BASE}/chat/cards/{c['card_id']}/confirm", headers=H, json={})
            print('CONFIRM', r.status_code, r.json().get('card', {}).get('status'))
            rules = requests.get(f'{BASE}/rules', headers=H).json()
            print('RULES', json.dumps(rules)[:500])
