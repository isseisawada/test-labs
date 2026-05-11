"""freee 認証デバッグ用スクリプト"""
import os
import requests
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path, override=True)

token = os.getenv("FREEE_ACCESS_TOKEN", "")
company_id = os.getenv("FREEE_COMPANY_ID", "")

print(f"FREEE_ACCESS_TOKEN : {'(空)' if not token else token[:20] + '...' }")
print(f"FREEE_COMPANY_ID   : {company_id or '(空)'}")

if not token:
    print("\n→ トークンが .env にありません。python3 -m freee_expense setup を実行してください。")
    exit(1)

# /api/1/users/me でトークンの有効性を確認
resp = requests.get(
    "https://api.freee.co.jp/api/1/users/me",
    headers={"Authorization": f"Bearer {token}"},
    timeout=10,
)
print(f"\n/api/1/users/me → HTTP {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"ログインユーザー: {data.get('user', {}).get('display_name', '')}")
    print("→ 認証OK！")
else:
    print(resp.text[:300])
    print("→ 認証失敗。トークンが無効です。再度 setup を実行してください。")
