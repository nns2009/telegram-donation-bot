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

router.all('/startPaymentTracking', koaBodyParser, async ctx => {
	const {
		address: addressString,
		callbackUrl,
		trackingState
	} = ctx.request.body;

	const address = Address.parse(addressString);

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
	
});

app.use(router.routes())
   .use(router.allowedMethods());

const serverPort = 7000;
app.listen(serverPort);
console.log('Payment tracker http-server started');
