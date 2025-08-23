import { Hono } from 'hono';
import { handle } from 'hono/aws-lambda';
import { HTTPException } from 'hono/http-exception';
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';

const app = new Hono();
const s3Client = new S3Client({ region: process.env.AWS_REGION_S3 || 'us-east-1' });

app.get('/', (c) => c.text('Hello from Hono on AWS Lambda!'));

app.post('/', async (c) => {
  const bot_token = process.env.SLACK_BOT_TOKEN;
  const channel_id = process.env.MAIN_CHANNEL_ID;
  if (!bot_token || !channel_id) {
    throw new HTTPException(500, { message: 'Internal service error' });
  }

  const { message, s3Url } = await c.req.json();
  if (!message) {
    return c.json({ error: 'message is required' }, 400);
  }

  let fileBlob = null;
  let fileName = null;

  // S3URLが提供された場合、画像を取得
  if (s3Url) {
    try {
      // S3 URLからバケット名とキーを抽出
      const url = new URL(s3Url);
      const pathParts = url.pathname.split('/').filter((part) => part !== '');
      const bucket = url.hostname.split('.')[0];
      const key = pathParts.join('/');
      fileName = pathParts[pathParts.length - 1];

      // S3でアクセスできるのは指定のバケットの下のファイルのみ
      const S3_BUCKET_SAVE_IMAGE = process.env.S3_BUCKET_SAVE_IMAGE || 'your-s3-bucket';
      if (bucket !== S3_BUCKET_SAVE_IMAGE) {
        throw new HTTPException(400, { message: 'invalid s3Url.' });
      }

      console.log(`Downloading from S3: bucket=${bucket}, key=${key}`);

      // S3から画像を取得
      const command = new GetObjectCommand({
        Bucket: bucket,
        Key: key,
      });

      const response = await s3Client.send(command);
      if (response.Body) {
        const chunks = [];
        const reader = response.Body.transformToWebStream().getReader();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          chunks.push(value);
        }

        const uint8Array = new Uint8Array(
          chunks.reduce((acc, chunk) => acc + chunk.length, 0),
        );
        let offset = 0;
        for (const chunk of chunks) {
          uint8Array.set(chunk, offset);
          offset += chunk.length;
        }

        fileBlob = new Blob([uint8Array], { type: response.ContentType || 'image/jpeg' });
      }
    } catch (error) {
      console.error('Error downloading from S3:', error);
      return c.json({ error: 'Failed to download image from S3' }, 500);
    }
  }

  // Slackに投稿
  if (fileBlob && fileName) {
    try {
      // Step 1: アップロードURLを取得
      console.log(`Getting upload URL for file: ${fileName}, size: ${fileBlob.size}`);

      const params = new URLSearchParams();
      params.append('filename', fileName);
      params.append('length', `${fileBlob.size}`);

      console.log(`Upload URL payload: ${JSON.stringify(params)}`);

      const getUploadUrlResponse = await fetch(
        'https://slack.com/api/files.getUploadURLExternal',
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${bot_token}`,
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: params,
        },
      );

      const getUploadUrlResult = await getUploadUrlResponse.json();
      console.log(`Upload URL response: ${JSON.stringify(getUploadUrlResult)}`);

      if (!getUploadUrlResult.ok) {
        throw new Error(`Failed to get upload URL: ${getUploadUrlResult.error}`);
      }

      // Step 2: ファイルをアップロード
      console.log(`Uploading file to Slack...`);
      const uploadResponse = await fetch(getUploadUrlResult.upload_url, {
        method: 'POST',
        body: fileBlob,
      });

      if (!uploadResponse.ok) {
        throw new Error(`Failed to upload file: ${uploadResponse.statusText}`);
      }

      // Step 3: アップロードを完了
      console.log(`Completing upload...`);
      const completeUploadResponse = await fetch(
        'https://slack.com/api/files.completeUploadExternal',
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${bot_token}`,
            'Content-Type': 'application/json; charset=utf-8',
          },
          body: JSON.stringify({
            files: [
              {
                id: getUploadUrlResult.file_id,
                title: fileName,
              },
            ],
          }),
        },
      );

      const completeUploadResult = await completeUploadResponse.json();
      console.log(`Complete upload response: ${JSON.stringify(completeUploadResult)}`);

      if (!completeUploadResult.ok) {
        throw new Error(`Failed to complete upload: ${completeUploadResult.error}`);
      }

      // Step 4: メッセージと共にファイルを投稿
      console.log(`Posting message with file...`);
      const postMessageResponse = await fetch('https://slack.com/api/chat.postMessage', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${bot_token}`,
          'Content-Type': 'application/json; charset=utf-8',
        },
        body: JSON.stringify({
          channel: channel_id,
          text: message,
          files: [
            {
              id: completeUploadResult.files[0].id,
            },
          ],
        }),
      });

      const postMessageResult = await postMessageResponse.json();
      console.log(`Post message response: ${JSON.stringify(postMessageResult)}`);

      return c.json({
        result: postMessageResponse.status,
        response: postMessageResult,
      });
    } catch (error) {
      console.error('Error uploading file to Slack:', error);
      return c.json({ error: 'Failed to upload file to Slack' }, 500);
    }
  } else {
    // テキストのみの投稿
    const payload = { channel: channel_id, text: message };

    console.log(`post request to slack. params => ${JSON.stringify(payload)}`);
    const response = await fetch('https://slack.com/api/chat.postMessage', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${bot_token}`,
        'Content-type': 'application/json; charset=utf-8',
      },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    console.log(`response from slack. ${response.status} ${JSON.stringify(result)}`);
    return c.json({
      result: response.status,
      response: result,
    });
  }
});

// Lambda handler
export const handler = handle(app);
