"""Dev helper: create (or reuse) Clerk test users and print short-lived session tokens. Never prints secrets."""
import os, sys, json, urllib.request, urllib.error, urllib.parse
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
SK = os.environ["CLERK_SECRET_KEY"]


def bapi(path, body=None, method="POST"):
    req = urllib.request.Request("https://api.clerk.com/v1" + path, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"Authorization": "Bearer " + SK, "Content-Type": "application/json", "User-Agent": "konnto-test"})
    return json.load(urllib.request.urlopen(req))


def get_or_create(email, first, password="Konnto-test-12345!"):
    found = bapi(f"/users?email_address={urllib.parse.quote(email)}", method="GET")
    if found:
        return found[0]
    return bapi("/users", {"email_address": [email], "password": password, "skip_password_checks": True, "first_name": first})


def token_for(user_id, secs=3600):
    s = bapi("/sessions", {"user_id": user_id})
    return bapi(f"/sessions/{s['id']}/tokens", {"expires_in_seconds": secs})["jwt"]


def ticket_for(user_id):
    return bapi("/sign_in_tokens", {"user_id": user_id, "expires_in_seconds": 3600})["token"]


if __name__ == "__main__":
    import urllib.parse
    email, first = sys.argv[1], sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "token"
    u = get_or_create(email, first)
    print(token_for(u["id"]) if mode == "token" else ticket_for(u["id"]))
