import { Hono } from 'hono';
import { handle } from 'hono/aws-lambda';

const app = new Hono();

app.get('/', (c) => c.text('Hello from Hono on AWS Lambda!'));

// Lambda handler
export const handler = handle(app);
