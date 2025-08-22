# Lambda関数のデプロイ方法

このプロジェクトでは、GitHub Actionsを使用して複数のLambda関数を自動デプロイします。

## 現在デプロイされている関数

- `hello-lambda-function`: 基本的なLambda関数（`./hello_lambda`）
- `hello-slack-function`: Slackにメッセージを投稿するLambda関数（`./hello_slack`）

## 新しいLambda関数を追加する手順

### 1. 関数ディレクトリの作成

```bash
mkdir new_function_name
cd new_function_name
```

### 2. 必要なファイルを作成

#### `app.py` - メイン関数ファイル
```python
import json

def lambda_handler(event, context):
    """
    Lambda関数のメインハンドラー
    """
    try:
        # ここに関数のロジックを記述
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Success'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
```

#### `requirements.txt` - 依存関係
```
# 必要なパッケージを記述
# 例: requests==2.31.0
```

#### `__init__.py` - 空ファイル
```bash
touch __init__.py
```

### 3. ワークフローに関数を追加

`.github/workflows/lambda_deploy_multi.yml`のmatrix部分に新しい関数を追加：

```yaml
strategy:
  matrix:
    function:
      - name: hello-lambda-function
        directory: ./hello_lambda
        handler: app.lambda_handler
      - name: hello-slack-function
        directory: ./hello_slack
        handler: app.lambda_handler
      - name: new-function-name  # ← 新しい関数を追加
        directory: ./new_function_name
        handler: app.lambda_handler  # または適切なハンドラー名
```

### 4. デプロイ実行

```bash
git add .
git commit -m "Add new Lambda function: new_function_name"
git push origin main
```

## 自動デプロイの仕組み

- **トリガー**: `main`ブランチへのプッシュ, プルリクエストの承認
- **並列実行**: 全ての関数が同時にデプロイされる
- **手動実行**: GitHub ActionsのUIから「workflow_dispatch」で手動実行可能

## 環境変数の設定

Lambda関数で環境変数が必要な場合：

1. AWSマネジメントコンソールでLambda関数を開く
2. 「設定」→「環境変数」で追加
3. または、ワークフローファイルに`environment`セクションを追加

## トラブルシューティング

### デプロイが失敗する場合

1. **IAMロール**: `LAMBDA_ROLE_ARN`がGitHub Secretsに正しく設定されているか確認
2. **ディレクトリ構造**: 関数ディレクトリに必要なファイルが揃っているか確認
3. **ハンドラー名**: `handler`パラメータが正しいか確認（`ファイル名.関数名`）

### ログの確認

- GitHub Actions: リポジトリの「Actions」タブでワークフローの実行ログを確認
- AWS CloudWatch: Lambda関数の実行ログを確認

## プロジェクト構造

```
project/
├── hello_lambda/          # 基本Lambda関数
│   ├── app.py
│   ├── requirements.txt
│   └── __init__.py
├── hello_slack/           # Slack投稿Lambda関数
│   ├── app.py
│   ├── requirements.txt
│   └── __init__.py
├── .github/workflows/
│   └── lambda_deploy_multi.yml  # デプロイワークフロー
└── README.md
```
