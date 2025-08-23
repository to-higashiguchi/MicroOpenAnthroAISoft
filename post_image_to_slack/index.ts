import { Hono } from 'hono';
import { handle } from 'hono/aws-lambda';
import { HTTPException } from 'hono/http-exception';

const app = new Hono();

app.get('/', (c) => c.text('Hello from Hono on AWS Lambda!'));

app.post('/', async (c) => {
  const bot_token = process.env.SLACK_BOT_TOKEN;
  const channel_id = process.env.MAIN_CHANNEL_ID;
  if (!bot_token || !channel_id) {
    throw new HTTPException(500, { message: 'Internal service error' });
  }

  const message = await c.req.json();
  if (!message) {
    return c.json({ error: 'message is required' }, 400);
  }

  const payload = { channel: channel_id, text: message };


  console.log(`post request to slack. params => ${JSON.stringify(payload)}`)
  const response = await fetch('https://jsonplaceholder.typicode.com/posts', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${bot_token}`,
      'Content-type': 'application/json; charset=utf-8',
    },
    body: JSON.stringify(payload),
  });

  console.log(`response from slack. ${response.status} ${response.body}`)
  return c.json({
    result: response.status,
  });
});

// Lambda handler
export const handler = handle(app);
