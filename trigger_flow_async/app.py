import json
import os
import hmac
import hashlib
import time
import requests
from urllib.parse import parse_qs

# 環境変数からSigning Secretを取得
SLACK_SIGNING_SECRET = os.environ['SLACK_SIGNING_SECRET']

# 長時間処理用Lambda関数の名前
LONG_PROCESSING_LAMBDA_NAME = os.environ['LONG_PROCESSING_LAMBDA_NAME']

def lambda_handler(event, context):
    # 1. POSTメソッドの検証
    if event['requestContext']['http']['method'] != 'POST':
        return {
            'statusCode': 405,
            'body': 'Method Not Allowed'
        }

    # 2. Slackからのリクエストであることを検証
    slack_timestamp = event['headers'].get('x-slack-request-timestamp')
    slack_signature = event['headers'].get('x-slack-signature')

    # ヘッダーが存在しない場合は検証失敗
    if not slack_timestamp or not slack_signature:
        return {
            'statusCode': 403,
            'body': 'Required Slack headers not found.'
        }

    # リプレイアタックを防ぐためのタイムスタンプチェック
    if abs(int(time.time()) - int(slack_timestamp)) > 60 * 5:
        return {
            'statusCode': 400,
            'body': 'Request time is too old.'
        }

    # 署名文字列を生成（バージョン識別子 + タイムスタンプ + 生のボディ）
    # Lambda関数URLのevent['body']は生のURLエンコードされた文字列
    sig_basestring = f'v0:{slack_timestamp}:{event["body"]}'

    # HMAC-SHA256でハッシュ化
    my_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # 生成した署名とSlackからの署名を比較
    if not hmac.compare_digest(my_signature, slack_signature):
        return {
            'statusCode': 403,
            'body': 'Signature Mismatch.'
        }

    # リクエストが正当であることを確認した後の処理

    # SlackからのリクエストボディはURLエンコードされているためデコード
    body_decoded = parse_qs(event['body'])

    # 非同期実行用のペイロードを準備
    payload = {
        'response_url': body_decoded['response_url'][0],
        'user_id': body_decoded['user_id'][0],
        'text': body_decoded.get('text', [''])[0],
    }

    # boto3を使って非同期で別のLambdaを呼び出す
    import boto3
    lambda_client = boto3.client('lambda')

    lambda_client.invoke(
        FunctionName=LONG_PROCESSING_LAMBDA_NAME,
        InvocationType='Event',  # 非同期呼び出し
        Payload=json.dumps(payload)
    )

    # 3秒以内にSlackにレスポンスを返す
    return {
        'statusCode': 200,
        'body': '{"text": "処理を開始しました。完了までしばらくお待ちください..."}'
    }