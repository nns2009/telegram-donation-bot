import fetch from 'node-fetch';
import BN from "bn.js";

import Koa from 'koa';
import koaBody from 'koa-body';
import Router from 'koa-router';

import { Address, TonClient, Wallet, WalletContract } from "ton";

import { tonClient } from "./TONParameters.js";
import { PaymentProcessor } from "../ton_payments/PaymentProcessor.js";
import { retrierFactory, sleep } from './common.js';


const maxSendRetries = 3;

const retrier = retrierFactory(maxSendRetries, 25);


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
				payments: paymentsUpdate.payments.map(p => ({
					...p,
					source: p.source.toFriendly(),
				})),
				address: addressString,
			}),
		}),
	);

	ctx.body = 'OK';
});

async function confirmedSend(wallet: Wallet, params: {
	sourceKey: Buffer,
	destinationAddress: Address,
	amount: number | string,
	message?: string,
	senderPaysFees: boolean,
}) {
	const {
		sourceKey,
		destinationAddress,
		amount,
		message,
		senderPaysFees,
	} = params;

	const startingSeqno = await wallet.getSeqNo();

	for (let i = 0; i < maxSendRetries; i++) {
		await wallet.transfer({
			bounce: false,
			secretKey: sourceKey,
			seqno: startingSeqno,
			to: destinationAddress,
			value: new BN(amount),
			payload: message,
			sendMode: 2 + (senderPaysFees ? 1 : 0),
		});

		for (let j = 0; j < 3; j++) {
			await sleep(20);
	
			const currentSeqno = await wallet.getSeqNo();
			if (currentSeqno > startingSeqno) {
				if (currentSeqno === startingSeqno + 1)
					return { seqno: startingSeqno };
				else
					throw new Error(`Parallel (multiple transfers at the same time) transfers are not allowed`);
			}
		}
	}

	await sleep(60);
	// wait extra, so 20*3+60=120 seconds pass since the last attempt,
	// which is more than 60 seconds (default validity period)
	// and we can be quite sure, that if 'seqno' hasn't changed
	// then transaction won't be accepted some time later
	const currentSeqno = await wallet.getSeqNo();
	if (currentSeqno > startingSeqno) {
		if (currentSeqno === startingSeqno + 1)
			return { seqno: startingSeqno };
		else
			throw new Error(`Parallel (multiple transfers at the same time) transfers are not allowed`);
	}

	return false;
}

router.all('/send', koaBodyParser, async ctx => {
	console.log(typeof ctx.request.body, ctx.request.body);
	let {
		sourceKey: sourceKeyString,
		destinationAddress: destinationAddressString,
		amount,
		message,
		senderPaysFees,
	} = ctx.request.body;

	if (!sourceKeyString)
		throw new Error(`Missing sourceKey`);
	const sourceKey = Buffer.from(sourceKeyString, 'hex');
	console.log('sourceKey:', sourceKey);

	const wallet = await retrier(
		() => Wallet.findBestBySecretKey(tonClient, 0, sourceKey));
	console.log('sourceAddress:', wallet.address);

	if (!destinationAddressString)
		throw new Error('Missing destinationAddress');
	const destinationAddress = Address.parse(destinationAddressString);
	console.log('destinationAddress:', destinationAddress);

	if (amount == undefined)
		throw new Error('Missing amount');

	if (senderPaysFees == undefined)
		throw new Error('Missing senderPaysFees');
	
	if (typeof senderPaysFees === 'string') {
		senderPaysFees = senderPaysFees.toLowerCase();
		if (senderPaysFees === 'true' || senderPaysFees === '1')
			senderPaysFees = true;
		else if (senderPaysFees === 'false' || senderPaysFees === '0')
			senderPaysFees = false;
		else
			throw new Error(`senderPaysFees can be one of: true | false | 0 | 1, not: ${senderPaysFees}`);
	}

	const sendResult = await confirmedSend(wallet, {
		sourceKey,
		destinationAddress,
		amount,
		message,
		senderPaysFees,
	});

	if (sendResult) {
		ctx.body = sendResult;
		console.log('Transaction successfull');
	} else {
		ctx.response.status = 400;
		ctx.response.body = `Transfer unsuccessfull`;
		console.error('Transaction failed');
	}
});

app.use(router.routes())
   .use(router.allowedMethods());

app.use(ctx => {
	console.warn('startWebhooks', `koa-router didn't catch this request:`, null, ctx.url);
});

const serverPort = 7000;
app.listen(serverPort);
console.log('Payment tracker http-server started');
