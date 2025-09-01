# 各Lambdaコードの概要

## dify_authorizer
Lambda Authorizer用の関数
difyでLambdaをHTTPリクエストで使用する場合に使用する

## dify_slack_bot_mention
SlackのメンションをトリガーにしてDifyのチャットボットを呼び出す関数

## dify_slack_bot_processer
SlackのメンションからDifyのチャットボットを呼び出した後のレスポンスを処理する関数
Slcakでは，リクエスト後数秒以内にレスポンスがないとエラーになってしまうため，`dify_slack_bot_mention`でとりあえずレスポンスを返し，
この関数でDifyのチャットボットからのレスポンスを受け取って，Slackに再度レスポンスを返す

## gen_image
画像生成を呼び出す関数．Nova Canvasを使用

## get_messages
Slackのチャンネルから指定した時間分の過去のメッセージを取得

## get_reactions
Slackのメッセージに付与されたリアクションを取得

## hello_lambda
Lambdaの動作確認用の関数

## hello_slack
Slackの動作確認用の関数

## post_image_to_slack
Slackに画像を投稿する関数

## trigger_flow
 /コマンドでSlackアプリを動作させるための処理．未完成．