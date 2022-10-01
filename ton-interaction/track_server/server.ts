import fetch from 'node-fetch';

import Koa from 'koa';
import koaBody from 'koa-body';
import Router from 'koa-router';

import { Address } from "ton";

import { tonClient } from "./TONParameters.js";
import { PaymentProcessor } from "../ton_payments/PaymentProcessor.js";


const app = new Koa();
const koaBodyParser = koaBody();
const router = new Router();

const paymentProcessor = new PaymentProcessor(tonClient, {});

router.all('/currentTrackingStateOf', async ctx => {
	const addressString = ctx.request.query.address;
	if (Array.isArray(addressString))
		throw new Error(`address shouldn't be ana array, but it is: ${addressString}`);
	if (addressString == undefined)
		throw new Error(`address url parameter must be specified, but it is not`);
	
	const address = Address.parse(addressString);
	const trackingState = await paymentProcessor.currentTrackingStateOf(address);

	ctx.body = trackingState;
});

router.all('/startPaymentTracking', koaBodyParser, async ctx => {
	console.log(typeof ctx.request.body, ctx.request.body);
	let {
		address: addressString,
		callbackUrl,
		trackingState
	} = ctx.request.body;

	const address = Address.parse(addressString);

	if (!addressString)
		throw new Error(`address param is mandatory`);
	if (!callbackUrl)
		throw new Error(`callbackUrl param is mandatory`);
	if (!trackingState)
		throw new Error(`Tracking state is mandatory`);

	if (typeof trackingState === 'string') {
		if (trackingState === 'current')
			trackingState = await paymentProcessor.currentTrackingStateOf(address);
		else
			throw new Error(`trackingState is unknown string: "${trackingState}"`);
	}

	paymentProcessor.startPaymentTracking(
		address, trackingState,
		paymentsUpdate => fetch(callbackUrl, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				...paymentsUpdate,
				address: addressString,
			}),
		}),
	);

	ctx.body = 'OK';
});

app.use(router.routes())
   .use(router.allowedMethods());

app.use(ctx => {
	console.warn('startWebhooks', `koa-router didn't catch this request:`, null, ctx.url);
});

const serverPort = 7000;
app.listen(serverPort);
console.log('Payment tracker http-server started');
