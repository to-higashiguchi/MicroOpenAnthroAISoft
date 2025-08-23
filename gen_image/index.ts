import { Hono } from 'hono';
import { handle } from 'hono/aws-lambda';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import {
  BedrockRuntimeClient,
  InvokeModelCommand,
} from '@aws-sdk/client-bedrock-runtime';

const app = new Hono();

app.get('/', (c) => c.text('Hello from Hono on AWS Lambda!'));

app.post('/generate', async (c) => {
  try {
    // 1. パラメータ取得
    const { prompt } = await c.req.json();
    if (!prompt) {
      return c.json({ error: 'prompt is required' }, 400);
    }
    console.log(`receive request. params=> ${JSON.stringify({ prompt })}`)

    // 2. Bedrock Nova Canvas呼び出し
    const bedrock = new BedrockRuntimeClient({
      region: process.env.AWS_REGION_BEDROCK || 'us-east-1',
    });
    const modelId = 'amazon.nova-canvas-v1:0'; // Nova CanvasのモデルID

    const bedrockParams = {
      taskType: 'TEXT_IMAGE',
      textToImageParams: {
        text: prompt,
        // negativeText: '', // 生成される画像から除外したい要素を指定するネガティブプロンプト
      },
      imageGenerationConfig: {
        numberOfImages: 1,
        quality: 'standard',
        cfgScale: 8.0,
        height: 1024,
        width: 1024,
        seed: Math.floor(Math.random() * 1000000),
      },
    };

    console.log(`request to Bedrock. params=> ${JSON.stringify(bedrockParams)}`);
    const bedrockRes = await bedrock.send(
      new InvokeModelCommand({
        modelId,
        contentType: 'application/json',
        accept: 'application/json',
        body: JSON.stringify(bedrockParams),
      }),
    );

    // Bedrockのレスポンスから画像データ取得
    const resJson = JSON.parse(new TextDecoder().decode(bedrockRes.body));
    const base64Image = resJson?.images?.[0];
    if (!base64Image) {
      throw new Error('No image returned from Bedrock');
    }

    const imageBuffer = Buffer.from(base64Image, 'base64');

    // 3. S3にアップロード
    const s3 = new S3Client({});
    const bucket = process.env.S3_BUCKET_SAVE_IMAGE || 'your-s3-bucket';
    const key = `generated/${Date.now()}-${Math.random().toString(36).slice(2)}.png`;
    console.log(`save image to S3. params=> ${JSON.stringify({
        Bucket: bucket,
        Key: key,
    })}`);

    await s3.send(
      new PutObjectCommand({
        Bucket: bucket,
        Key: key,
        Body: imageBuffer,
        ContentType: 'image/png',
      }),
    );

    // 4. S3パスを返す
    const s3Url = `s3://${bucket}/${key}`;
    console.log(`send response. params=> ${JSON.stringify({ s3Url })} `)
    return c.json({
      success: true,
      s3Url,
      prompt,
    });
  } catch (error) {
    console.error('Error generating image:', error);
    return c.json(
      {
        error: 'Failed to generate image',
        detail: error instanceof Error ? error.message : String(error),
      },
      500,
    );
  }
});

// Lambda handler
export const handler = handle(app);
