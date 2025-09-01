import json
import boto3
import os

# Secrets Managerからシークレット名を取得
SECRET_NAME = os.environ["SECRET_NAME"]
secrets_client = boto3.client("secretsmanager")


def get_secret_key():
    """Secrets ManagerからAPIキーを取得"""
    try:
        response = secrets_client.get_secret_value(SecretId=SECRET_NAME)
        secret = json.loads(response["SecretString"])
        return secret["api_key"]
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        raise e


def lambda_handler(event, context):
    try:
        # 正しいAPIキーを取得
        valid_api_key = get_secret_key()

        # Difyから送られてきたヘッダーの値を取得
        # ヘッダー名はAPI Gatewayによって小文字に変換されます
        received_key = event["headers"].get("x-dify-secret-key")

        # Difyからのキーと正しいキーを比較
        if received_key and received_key == valid_api_key:
            # 認証成功
            print("Authorization successful.")
            return {"isAuthorized": True}
        else:
            # 認証失敗
            print("Authorization failed: Invalid or missing secret key.")
            return {"isAuthorized": False}

    except Exception as e:
        print(f"An error occurred in the authorizer: {e}")
        # 不測のエラー時もアクセスを拒否
        return {"isAuthorized": False}
