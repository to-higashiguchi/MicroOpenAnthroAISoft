##################################################
# 設定した期間内のSlackチャンネルのメッセージを取得するLambda関数
##################################################

import os
import json
import time
from datetime import datetime, timedelta, timezone
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# 遡ってメッセージを取得する期間（分数）
MINUTES_TO_FETCH = 120


def fetch_slack_messages(token, channel_id, minutes):
    """
    指定されたSlackチャンネルのメッセージを取得して出力します。
    Lambda用に結果も返します。
    """
    result = {
        "channel_id": channel_id,
        "minutes": minutes,
        "messages": [],
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
        # conversations.history APIで指定期間のメッセージを取得
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
            return result

        print(f"👍 {len(messages)}件のメッセージが見つかりました。")
        print("-" * 40)

        result["summary"]["message_count"] = len(messages)

        # メッセージの詳細を処理
        for message in messages:
            message_ts = message["ts"]
            user_id = message.get("user", "unknown")
            text = message.get("text", "")

            # タイムスタンプを日時に変換
            message_datetime = datetime.fromtimestamp(float(message_ts), tz=jst)
            formatted_time = message_datetime.strftime("%Y/%m/%d %H:%M:%S")

            # ユーザー情報を取得（可能であれば）
            user_name = user_id
            try:
                if user_id != "unknown":
                    user_info = client.users_info(user=user_id)
                    user_name = (
                        user_info["user"]["real_name"] or user_info["user"]["name"]
                    )
                    # APIレート制限を避けるため少し待機
                    time.sleep(0.5)
            except SlackApiError:
                # ユーザー情報が取得できない場合はIDをそのまま使用
                pass

            message_data = {
                "timestamp": message_ts,
                "datetime": formatted_time,
                "user_id": user_id,
                "user_name": user_name,
                "text": text,
                "has_reactions": bool(message.get("reactions")),
                "reaction_count": sum(
                    len(r.get("users", [])) for r in message.get("reactions", [])
                ),
            }

            # スレッドメッセージの場合
            if message.get("thread_ts"):
                message_data["is_thread_reply"] = True
                message_data["thread_ts"] = message["thread_ts"]
            else:
                message_data["is_thread_reply"] = False

            # ファイルが添付されている場合
            if message.get("files"):
                message_data["has_files"] = True
                message_data["file_count"] = len(message["files"])
            else:
                message_data["has_files"] = False
                message_data["file_count"] = 0

            result["messages"].append(message_data)

            print(
                f"📝 [{formatted_time}] {user_name}: {text[:50]}{'...' if len(text) > 50 else ''}"
            )

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

        # Slackからメッセージ情報を取得
        result = fetch_slack_messages(slack_bot_token, channel_id, minutes)

        # APIエラーなどがresultに含まれている場合はエラーとして返す
        if "error" in result and not result.get("messages"):
            return {
                "statusCode": 500,
                "body": json.dumps({"error": result["error"]}),
            }

        # resultからmessagesのリストのみを抽出
        messages_list = result.get("messages", [])

        # 変更点: レスポンスボディにはmessagesのリストのみを含める
        return {
            "statusCode": 200,
            "body": json.dumps(
                messages_list,
                ensure_ascii=False,  # 日本語のテキストが文字化けしないように設定
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
    # 実行前に環境変数を設定してください
    # export SLACK_BOT_TOKEN="xoxb-your-token"
    # export MAIN_CHANNEL_ID="C12345678"

    test_event = {"minutes": 30}
    test_context = {}
    result = lambda_handler(test_event, test_context)
    print("--- Lambda Response ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # bodyの中身をパースして確認
    if result.get("statusCode") == 200 and "body" in result:
        print("\n--- Parsed Body Content ---")
        try:
            body_content = json.loads(result["body"])
            print(json.dumps(body_content, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print("Body is not a valid JSON.")
