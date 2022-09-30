import { Address, Cell, toNano, TonClient, Traits } from "ton";

import { addressEqual, sleep } from "./shared.js";
import * as Transaction from './Transaction.js';
import { TransactionId } from "./Transaction.js";



export type TrackingState = {
	lastProcessedLt?: string,
};

export type Payment = {
	source: Address,
	amount: number,
	message: string,
};

export type PaymentsUpdate = {
	payments: Payment[],
	nextTrackingState: TrackingState,
}

export type PaymentReceivedCallback =
	(paymentsUpdate: PaymentsUpdate) => void;

	
export const defaultTrackingState: TrackingState = {
	lastProcessedLt: undefined,
};

export class PaymentProcessor {
	tonClient: TonClient;
	checkIntervalInSeconds: number;
	chunkSize: number;

	constructor(tonClient: TonClient, params: {
		checkIntervalInSeconds?: number,
		chunkSize?: number,
	}) {
		this.tonClient = tonClient;
		this.checkIntervalInSeconds = params.checkIntervalInSeconds ?? 20;
		this.chunkSize = params.chunkSize ?? 25;
	}

	async newPaymentsTo(
		address: Address,
		trackingState: TrackingState,
	): Promise<PaymentsUpdate> {
		const untilId: TransactionId = (await Transaction.last(this.tonClient, address)).id;

		const transactions = await Transaction.getAllSince(
			this.tonClient, address, this.chunkSize, trackingState.lastProcessedLt, untilId, true);

		const payments: Payment[] = [];

		for (const tr of transactions) {
			if (!tr.inMessage) // How can it even be possible?
				continue;
			if (!addressEqual(tr.inMessage.destination, address))
				continue;
			if (tr.inMessage.source == null)
				continue;
			if (addressEqual(tr.inMessage.source, address))
				continue;

			const body = tr.inMessage.body;
			if (!body) // Empty messages without comment
				continue;
			if (body.type !== 'text')
				continue;

			payments.push({
				source: tr.inMessage.source,
				amount: tr.inMessage.value.toNumber(),
				message: body.text,
			});
		}

		return {
			payments,
			nextTrackingState: {
				lastProcessedLt: untilId.lt,
			},
		};
	}
	
	async startPaymentTracking(
		address: Address,
		trackingState: TrackingState,
		callback: PaymentReceivedCallback,
	): Promise<void> {
		while (true) {
			const paymentsUpdate = await this.newPaymentsTo(address, trackingState);
			await callback(paymentsUpdate);

			trackingState = paymentsUpdate.nextTrackingState;
			await sleep(this.checkIntervalInSeconds);
		}
	}
}

