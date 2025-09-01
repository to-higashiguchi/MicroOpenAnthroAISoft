import json
import os
import urllib3

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
DIFY_API_KEY = os.environ["DIFY_API_KEY"]
DIFY_API_URL = os.environ["DIFY_API_URL"]

http = urllib3.PoolManager()


def lambda_handler(event, context):

    # 受付係から渡された情報を受け取る
    # question = event['question']
    # channel_id = event['channel_id']
    # user_id = event['user_id']
    # message_ts = event['message_ts']  # ★メッセージのタイムスタンプを受け取る

    # 受付係から渡された情報を受け取る（SQS経由）
    # messageは json string なので辞書に変換
    try:
        message_body = json.loads(event["Records"][0]["body"])
    except json.JSONDecodeError:
        print("Failed to decode JSON from the message body.")
        return {"statusCode": 400, "body": "Invalid message body."}
    question = message_body["question"]
    channel_id = message_body["channel_id"]
    user_id = message_body["user_id"]
    message_ts = message_body["message_ts"]  # ★メッセージのタイムスタンプを受け取る

    try:
        dify_response_text = call_dify_api(question, user_id)

        # Difyから有効な回答があった場合
        if dify_response_text:
            # ★既存のメッセージをDifyの回答に更新する
            update_slack_message(
                channel_id, message_ts, f"<@{user_id}> {dify_response_text}"
            )
        # Difyから回答がなかった場合
        else:
            # ★「考え中...」メッセージを削除して、何もなかったことにする
            delete_slack_message(channel_id, message_ts)

    except Exception as e:
        print(f"An exception occurred: {e}")
        # ★エラーが発生した場合は、メッセージを更新してユーザーに知らせる
        update_slack_message(
            channel_id, message_ts, f"<@{user_id}> ごめんなさい、エラーが発生しました。"
        )

    return {"statusCode": 200, "body": "Processing complete."}


def call_dify_api(query, user_id):
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": {"question": query},
        "response_mode": "streaming",
        "user": f"slack-{user_id}",
    }
    response = http.request(
        "POST", DIFY_API_URL, headers=headers, body=json.dumps(payload).encode("utf-8")
    )

    # Difyからの応答がエラーでないことを確認
    if response.status >= 300:
        print(f"Dify API returned an error status: {response.status}")
        return ""  # エラーの場合は空文字を返す

    full_response = ""
    for line in response.data.decode("utf-8").strip().split("\n"):
        if line.startswith("data:"):
            try:
                data_json = json.loads(line[len("data: ") :])
                if "answer" in data_json:
                    full_response += data_json["answer"]
            except json.JSONDecodeError:
                continue
    # ★変更点: Difyからの応答がない場合は、特定の文字列ではなく空文字を返すようにします
    return full_response


# ★関数をsendからupdateとdeleteに変更
def update_slack_message(channel_id, ts, text):
    """既存のSlackメッセージを更新する"""
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"channel": channel_id, "ts": ts, "text": text}
    http.request(
        "POST",
        "https://slack.com/api/chat.update",  # chat.update API を使用
        headers=headers,
        body=json.dumps(payload).encode("utf-8"),
    )


def delete_slack_message(channel_id, ts):
    """既存のSlackメッセージを削除する"""
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"channel": channel_id, "ts": ts}
    http.request(
        "POST",
        "https://slack.com/api/chat.delete",  # chat.delete API を使用
        headers=headers,
        body=json.dumps(payload).encode("utf-8"),
    )
