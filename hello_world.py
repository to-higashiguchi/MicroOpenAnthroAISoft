"""
設定したチャンネルにBotがHello Worldを出力する
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# 自分の情報に書き換える
bot_token = os.environ.get("SLACK_BOT_TOKEN")
channel_id = os.environ.get("MAIN_CHANNEL_ID")

url = "https://slack.com/api/chat.postMessage"

headers = {
    "Authorization": f"Bearer {bot_token}",
    "Content-type": "application/json; charset=utf-8",
}

payload = {"channel": channel_id, "text": "Hello from Python! 🐍"}

response = requests.post(url, headers=headers, data=json.dumps(payload))

# レスポンスを確認
# ... (省略) ...
response_data = response.json()  # レスポンスを一度変数に入れる

if response.status_code == 200 and response_data.get("ok"):
    print("メッセージの投稿に成功しました。Slackからの応答:")
    print(response_data)  # ★★★ ここで応答全体を表示 ★★★
else:
    print("エラーが発生しました:", response_data.get("error"))
