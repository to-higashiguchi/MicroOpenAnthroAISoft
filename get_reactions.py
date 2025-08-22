################################################################################
# 設定した期間内のSlackチャンネルのメッセージとリアクションを取得して出力するスクリプト。
#
# 出力例
# ```
# ✅ チャンネル 'C01234ABCDE' のメッセージを取得します。
# ✅ 期間: 2025/08/15 〜 2025/08/22
# ----------------------------------------
# 📜 メッセージ履歴を取得中...
# 👍 5件のメッセージが見つかりました。リアクションを取得します。
# ----------------------------------------
#
# 💬 メッセージ: 「来週の定例会議のアジェンダです。...」
#    (リンク: https://your-workspace.slack.com/archives/C01234ABCDE/p1724314456789012)
#   - :eyes: by U012ABCDEF, U034GHIJKL
#   - :+1: by U012ABCDEF
#
# 💬 メッセージ: 「プロジェクトAの進捗報告を更新しました。...」
#    (リンク: https://your-workspace.slack.com/archives/C01234ABCDE/p1724215543210987)
#   - :white_check_mark: by U056MNOPQR
#
# ...
#
# ----------------------------------------
# ✅ 処理が完了しました。
# ```
#####################################################################################

import os
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta, timezone
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# 事前準備
load_dotenv()
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
CHANNEL_ID = os.environ.get("MAIN_CHANNEL_ID")

# 遡ってメッセージを取得する期間（日数）
DAYS_TO_FETCH = 7


def fetch_slack_reactions(token, channel_id, days):
    """
    指定されたSlackチャンネルのメッセージとリアクションを取得して出力します。
    """
    if not token:
        print("エラー: Slackボットトークンが設定されていません。")
        print("環境変数 `SLACK_BOT_TOKEN` を設定してください。")
        return

    client = WebClient(token=token)

    # タイムゾーンを考慮した期間設定（JST）
    jst = timezone(timedelta(hours=+9))
    now = datetime.now(jst)
    past_date = now - timedelta(days=days)

    # Unixタイムスタンプに変換
    latest_ts = now.timestamp()
    oldest_ts = past_date.timestamp()

    print(f"✅ チャンネル '{channel_id}' のメッセージを取得します。")
    print(f"✅ 期間: {past_date.strftime('%Y/%m/%d')} 〜 {now.strftime('%Y/%m/%d')}")
    print("-" * 40)

    try:
        # 1. conversations.history APIで指定期間のメッセージを取得
        print("📜 メッセージ履歴を取得中...")
        history_response = client.conversations_history(
            channel=channel_id,
            latest=str(latest_ts),
            oldest=str(oldest_ts),
            limit=200,  # 取得するメッセージ数の上限
        )
        messages = history_response.get("messages", [])

        if not messages:
            print("指定された期間にメッセージは見つかりませんでした。")
            return

        print(
            f"👍 {len(messages)}件のメッセージが見つかりました。リアクションを取得します。"
        )
        print("-" * 40)

        # 2. 取得した各メッセージに対してリアクション情報を取得
        for message in messages:
            # リアクションがついているメッセージのみ処理
            if message.get("reactions"):
                message_ts = message["ts"]
                message_text = message.get("text", "(テキストなし)").replace("\n", " ")

                # メッセージのパーマリンクを取得
                permalink_response = client.chat_getPermalink(
                    channel=channel_id, message_ts=message_ts
                )
                permalink = permalink_response.get("permalink", "")

                print(f"\n💬 メッセージ: 「{message_text[:60]}...」")
                print(f"   (リンク: {permalink})")

                try:
                    # reactions.get APIでリアクションの詳細を取得
                    # conversations.historyの応答にもリアクションは含まれますが、
                    # このメソッドを使うことでより詳細な情報が得られます。
                    reactions_response = client.reactions_get(
                        channel=channel_id, timestamp=message_ts, full=True
                    )

                    reactions_data = reactions_response.get("message", {}).get(
                        "reactions", []
                    )

                    if reactions_data:
                        for reaction in reactions_data:
                            name = reaction["name"]  # リアクション名
                            users = reaction["users"]
                            print(f"  - :{name}: by {', '.join(users)}")
                    else:
                        # このケースは通常 `message.get("reactions")` で弾かれるため稀
                        print("  - リアクション情報がありませんでした。")

                    # Slack APIのレートリミットを避けるための待機 (Tier3: 50+ req/min)
                    time.sleep(1.2)

                except SlackApiError as e:
                    print(f"  ❌ リアクション取得エラー: {e.response['error']}")

        print("\n" + "-" * 40)
        print("✅ 処理が完了しました。")

    except SlackApiError as e:
        error_type = e.response["error"]
        print(f"❌ APIエラーが発生しました: {error_type}")
        if error_type == "not_in_channel":
            print(
                f"エラー詳細: ボットがチャンネル '{channel_id}' に招待されていません。"
            )
        elif error_type == "invalid_auth":
            print(
                "エラー詳細: Slackトークンが無効です。正しいトークンか確認してください。"
            )
        elif error_type == "channel_not_found":
            print(f"エラー詳細: チャンネルID '{channel_id}' が見つかりません。")


if __name__ == "__main__":
    fetch_slack_reactions(SLACK_BOT_TOKEN, CHANNEL_ID, DAYS_TO_FETCH)
