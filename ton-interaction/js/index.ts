
import { Address } from "ton";
import { PaymentProcessor } from "../ton_payments/PaymentProcessor.js";
import { getTrackingState, processPayments } from "./api.js";
import { tonClient } from "./TONParameters.js";


const trackedAddress = Address.parse('EQAa_d5RopvY6ZLcQFNJHFmdA8wf_igH-V-5Jc8DRprJIZa-');

const trackingState = await getTrackingState(trackedAddress);

const paymentProcessor = new PaymentProcessor(tonClient, {});
paymentProcessor.startPaymentTracking(
	trackedAddress, trackingState,
	processPayments,
);
