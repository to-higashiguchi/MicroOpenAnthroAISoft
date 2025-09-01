import json
import os
import boto3
import urllib3

# ★★★ 実行係のLambda関数の名前に書き換えてください ★★★
PROCESSOR_FUNCTION_NAME = "dify-slack-bot-processor"
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]

sqs_client = boto3.client("sqs")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")

lambda_client = boto3.client("lambda")
http = urllib3.PoolManager()


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    if "challenge" in body:
        return {"statusCode": 200, "body": json.dumps({"challenge": body["challenge"]})}

    try:
        slack_event = body.get("event", {})

        # 봇 자신의 메시지나 재전송 이벤트에 응답하지 않도록 방지
        if slack_event.get(
            "subtype"
        ) == "bot_message" or "X-Slack-Retry-Num" in event.get("headers", {}):
            return {"statusCode": 200, "body": "ok"}

        question = slack_event.get("text", "").split(">", 1)[-1].strip()
        channel_id = slack_event.get("channel")
        user_id = slack_event.get("user")

        # 「考え中」メッセージを投稿し、その応答（メッセージ情報）を取得
        initial_message_response = post_slack_message(
            channel_id, f"<@{user_id}> 考え中... 🤔"
        )

        # 投稿したメッセージのタイムスタンプ（メッセージID）を取得
        message_ts = initial_message_response.get("ts")

        # タイムスタンプが正常に取得できた場合のみ、実行係を呼び出す
        if message_ts:
            # payload_for_processor = {
            #     'question': question,
            #     'channel_id': channel_id,
            #     'user_id': user_id,
            #     'message_ts': message_ts  # ★タイムスタンプを実行係に渡す
            # }
            # lambda_client.invoke(
            #     FunctionName=PROCESSOR_FUNCTION_NAME,
            #     InvocationType='Event',
            #     Payload=json.dumps(payload_for_processor)
            # )

            # 配信したいメッセージの本体
            # SQSのMessageBodyは文字列である必要があります。
            # 辞書などを送る場合は、json.dumps()で文字列に変換します。
            message_body = {
                "question": question,
                "channel_id": channel_id,
                "user_id": user_id,
                "message_ts": message_ts,
            }

            # メッセージを文字列に変換
            try:
                message_body_str = json.dumps(message_body)
            except TypeError as e:
                print(f"Error serializing message: {e}")
                return {
                    "statusCode": 500,
                    "body": json.dumps("Error serializing message body."),
                }

            # SQSにメッセージを送信
            try:
                response = sqs_client.send_message(
                    QueueUrl=QUEUE_URL,
                    MessageBody=message_body_str,
                    # MessageAttributes={
                    #     'attribute1': {
                    #         'StringValue': 'value1',
                    #         'DataType': 'String'
                    #     }
                    # }
                )

            except Exception as e:
                print(f"Error in responder function: {e}")

    except Exception as e:
        print(f"Unhandled error: {e}")

    # SlackにはすぐにOKを返す
    return {"statusCode": 200, "body": "ok"}


def post_slack_message(channel_id, text):
    """Slackにメッセージを投稿し、APIからの応答を返す"""
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"channel": channel_id, "text": text}

    response = http.request(
        "POST",
        "https://slack.com/api/chat.postMessage",
        headers=headers,
        body=json.dumps(payload).encode("utf-8"),
    )
    # 応答をJSONとして解釈して返す
    return json.loads(response.data.decode("utf-8"))
