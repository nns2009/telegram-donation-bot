import fetch from 'node-fetch';
import qs from 'qs';
import { Address } from 'ton';

import { PaymentsUpdate, TrackingState } from '../ton_payments/PaymentProcessor.js';


export type ObjectDict = { [key: string]: any };


const baseUrl = 'http://localhost:8000';

async function request<T>(method: string, params: ObjectDict): Promise<T> {
	const urlParamString = qs.stringify({
			...params,
		},
		{ encode: false },
	);
	const url = `${baseUrl}/${method}/?` + urlParamString;

	const resp = await fetch(url);
	const res = await resp.json() as T;
	return res;
}

export const getTrackingState = (address: Address) =>
	request<TrackingState>(
		'get-tracking-state',
		{ address: address.toFriendly() }
	);

export const processPayments = (paymentsUpdate: PaymentsUpdate) =>
	request('process-payments')
