import { TonClient } from "ton";


export const endpoint = "https://toncenter.com/api/v2/jsonRPC";
export const endpointApiKey = API_KEY_HERE;

export const workchain = 0;

export const tonClient = new TonClient({
	endpoint,
	apiKey: endpointApiKey,
});
