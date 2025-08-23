##################################################
# 設定した期間内のSlackチャンネルのメッセージとリアクションを取得するLambda関数
##################################################

import os
import json
import time
from datetime import datetime, timedelta, timezone
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# 遡ってメッセージを取得する期間（分数）
MINUTES_TO_FETCH = 30


def fetch_slack_reactions(token, channel_id, minutes):
    """
    指定されたSlackチャンネルのリアクションを取得して出力します。
    Lambda用に結果も返します。
    """
    result = {
        "channel_id": channel_id,
        "minutes": minutes,
        "reactions": [],
        "summary": {},
    }

    if not token:
        error_msg = "エラー: Slackボットトークンが設定されていません。"
        print(error_msg)
        result["error"] = error_msg
        return result

    client = WebClient(token=token)

    # タイムゾーンを考慮した期間設定（JST）
    jst = timezone(timedelta(hours=+9))
    now = datetime.now(jst)
    past_date = now - timedelta(minutes=minutes)

    # Unixタイムスタンプに変換
    latest_ts = now.timestamp()
    oldest_ts = past_date.timestamp()

    print(f"✅ チャンネル '{channel_id}' のメッセージを取得します。")
    print(
        f"✅ 期間: {past_date.strftime('%Y/%m/%d %H:%M')} 〜 {now.strftime('%Y/%m/%d %H:%M')}"
    )
    print("-" * 40)

    result["period"] = {
        "from": past_date.strftime("%Y/%m/%d %H:%M"),
        "to": now.strftime("%Y/%m/%d %H:%M"),
    }

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
            msg = "指定された期間にメッセージは見つかりませんでした。"
            print(msg)
            result["summary"]["message_count"] = 0
            result["summary"]["reaction_count"] = 0
            return result

        print(
            f"👍 {len(messages)}件のメッセージが見つかりました。リアクションを取得します。"
        )
        print("-" * 40)

        result["summary"]["message_count"] = len(messages)
        reaction_count = 0

        # 2. 取得した各メッセージに対してリアクション情報を取得
        for message in messages:
            # リアクションがついているメッセージのみ処理
            if message.get("reactions"):
                message_ts = message["ts"]

                try:
                    # reactions.get APIでリアクションの詳細を取得
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

                            result["reactions"].append(
                                {
                                    "name": name, 
                                    "users": users, 
                                    "count": len(users),
                                    "timestamp": message_ts
                                }
                            )
                            reaction_count += len(users)

                    # Slack APIのレートリミットを避けるための待機 (Tier3: 50+ req/min)
                    time.sleep(1.2)

                except SlackApiError as e:
                    error_msg = f"リアクション取得エラー: {e.response['error']}"
                    print(f"  ❌ {error_msg}")
                    # エラーは個別のリアクションではなく全体のエラーとして記録
                    if "error" not in result:
                        result["error"] = []
                    result["error"].append(error_msg)

        result["summary"]["reaction_count"] = reaction_count
        print("\n" + "-" * 40)
        print("✅ 処理が完了しました。")

        return result

    except SlackApiError as e:
        error_type = e.response["error"]
        error_msg = f"APIエラーが発生しました: {error_type}"
        print(f"❌ {error_msg}")

        if error_type == "not_in_channel":
            detail = f"ボットがチャンネル '{channel_id}' に招待されていません。"
            print(f"エラー詳細: {detail}")
            error_msg += f" - {detail}"
        elif error_type == "invalid_auth":
            detail = "Slackトークンが無効です。正しいトークンか確認してください。"
            print(f"エラー詳細: {detail}")
            error_msg += f" - {detail}"
        elif error_type == "channel_not_found":
            detail = f"チャンネルID '{channel_id}' が見つかりません。"
            print(f"エラー詳細: {detail}")
            error_msg += f" - {detail}"

        result["error"] = error_msg
        return result


def lambda_handler(event, context):
    """
    Lambda関数のメインハンドラー
    """
    try:
        # 環境変数から設定を取得
        slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
        channel_id = os.environ.get("MAIN_CHANNEL_ID")

        if not slack_bot_token or not channel_id:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "SLACK_BOT_TOKEN or MAIN_CHANNEL_ID environment variable not set"
                    }
                ),
            }

        # eventから期間を設定できるようにする（デフォルトは30分）
        minutes = event.get("minutes", MINUTES_TO_FETCH)

        # Slackからリアクション情報を取得
        result = fetch_slack_reactions(slack_bot_token, channel_id, minutes)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Successfully fetched Slack reactions", "reactions": result}
            ),
        }

    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal server error: {str(e)}"}),
        }


if __name__ == "__main__":
    # ローカル実行時のテスト用
    test_event = {"minutes": 30}
    test_context = {}
    result = lambda_handler(test_event, test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
