##################################################
# 設定したチャンネルにBotがHello Worldを出力するLambda関数
##################################################

import requests
import json
import os

def lambda_handler(event, context):
    """
    Lambda関数のメインハンドラー
    """
    try:
        # 環境変数から設定を取得
        bot_token = os.environ.get("SLACK_BOT_TOKEN")
        channel_id = os.environ.get("MAIN_CHANNEL_ID")
        
        if not bot_token or not channel_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'SLACK_BOT_TOKEN or MAIN_CHANNEL_ID environment variable not set'
                })
            }

        url = "https://slack.com/api/chat.postMessage"

        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-type": "application/json; charset=utf-8",
        }

        # eventからメッセージをカスタマイズできるようにする
        message = event.get('message', 'Hello from Python Lambda! 🐍')
        
        payload = {"channel": channel_id, "text": message}

        response = requests.post(url, headers=headers, data=json.dumps(payload))

        # レスポンスを確認
        response_data = response.json()

        if response.status_code == 200 and response_data.get("ok"):
            print("メッセージの投稿に成功しました。Slackからの応答:")
            print(response_data)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Successfully posted to Slack',
                    'slack_response': response_data
                })
            }
        else:
            error_msg = response_data.get("error", "Unknown error")
            print("エラーが発生しました:", error_msg)
            
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Slack API error: {error_msg}',
                    'slack_response': response_data
                })
            }
            
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }
