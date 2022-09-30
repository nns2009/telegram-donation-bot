import { TonClient } from "ton";


export const endpoint = "https://testnet.toncenter.com/api/v2/jsonRPC";
export const endpointApiKey = "30d51a64f3d182c1767fcdfd887656b35b669683f18dc1c75bc7c6fd33edf075";

export const workchain = 0;

export const tonClient = new TonClient({
	endpoint,
	apiKey: endpointApiKey,
});
