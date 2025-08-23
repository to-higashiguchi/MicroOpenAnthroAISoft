import { Hono } from 'hono';
import { handle } from 'hono/aws-lambda';
import { HTTPException } from 'hono/http-exception';
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';

const app = new Hono();
const s3Client = new S3Client({ region: process.env.AWS_REGION || 'us-east-1' });

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
      const pathParts = url.pathname.split('/').filter(part => part !== '');
      const bucket = url.hostname.split('.')[0];
      const key = pathParts.join('/');
      fileName = pathParts[pathParts.length - 1];

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
        
        const uint8Array = new Uint8Array(chunks.reduce((acc, chunk) => acc + chunk.length, 0));
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
    // 画像をSlackにアップロード
    const formData = new FormData();
    formData.append('file', fileBlob, fileName);
    formData.append('channels', channel_id);
    formData.append('initial_comment', message);

    console.log(`Uploading file to slack. filename => ${fileName}`);
    const uploadResponse = await fetch('https://slack.com/api/files.upload', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${bot_token}`,
      },
      body: formData,
    });

    const uploadResult = await uploadResponse.json();
    console.log(`response from slack file upload. ${uploadResponse.status} ${JSON.stringify(uploadResult)}`);
    
    return c.json({
      result: uploadResponse.status,
      response: uploadResult,
    });
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
