import fetch from 'node-fetch';

import Koa from 'koa';
import koaBody from 'koa-body';
import Router from 'koa-router';


const app = new Koa();
const koaBodyParser = koaBody();
const router = new Router();

const testPort = 10000;
const testCallbackMethod = 'test-callback';

router.all('/' + testCallbackMethod, koaBodyParser, async ctx => {
	console.log(`Received payment updates:`, ctx.request.body);
	ctx.body = 'OK';
});

app.use(router.routes())
   .use(router.allowedMethods());

app.use(ctx => {
	console.warn('startWebhooks', `koa-router didn't catch this request:`, null, ctx.url);
});

app.listen(testPort);
console.log('Test payment tracker http-server started');




const trackedAddressString = 'EQAa_d5RopvY6ZLcQFNJHFmdA8wf_igH-V-5Jc8DRprJIZa-'
const baseTrackerUrl = 'http://localhost:7000';

const initialTrackingState = await
	(await fetch(`${baseTrackerUrl}/currentTrackingStateOf?address=${trackedAddressString})`)).json();

await fetch(`${baseTrackerUrl}/startPaymentTracking`, {
	method: 'POST',
	headers: {
		'Content-Type': 'application/json',
	},
	body: JSON.stringify({
		address: trackedAddressString,
		trackingState: 'current', // initialTrackingState,
		callbackUrl: `http://localhost:${testPort}/${testCallbackMethod}`,
	}),
});

