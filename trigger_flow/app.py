##################################################
# フローを呼び出すLambda関数
##################################################

import os
import json
import requests


def lambda_handler(event, context):
    """
    Lambda関数のメインハンドラー
    """
    try:
        api_key = os.environ.get("DIFY_API_KEY")

        url = "https://event-dify.tech-gather.org/v1/workflows/run"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "inputs": {},
            "response_mode": "streaming",
            "user": "abc-123"
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(data), stream=False)
        
        if response.status_code == 200:
            print("Success to call.")
        else:
            print(f"Error: Status code {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal server error: {str(e)}"}),
        }


if __name__ == "__main__":
    # ローカル実行時のテスト用
    lambda_handler(None, None)

