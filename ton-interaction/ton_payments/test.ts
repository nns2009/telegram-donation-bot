import { Address } from "ton";

import { tonClient } from "./TONParameters.js";
import { PaymentProcessor } from "./PaymentProcessor.js";

const trackedAddress = Address.parse('EQAa_d5RopvY6ZLcQFNJHFmdA8wf_igH-V-5Jc8DRprJIZa-');

const paymentProcessor = new PaymentProcessor(tonClient, {
	checkIntervalInSeconds: 90,
});

const trackingState = await paymentProcessor.currentTrackingStateOf(trackedAddress);

console.log(`Tracking address:`, trackedAddress.toFriendly());
console.log(`Initial tracking state is:`, trackingState);

paymentProcessor.startPaymentTracking(
	trackedAddress, trackingState,
	paymentsUpdate => {
		console.log(`Received paymentsUpdate:`, paymentsUpdate);
	}
);
console.log(`Started payment tracking`);
