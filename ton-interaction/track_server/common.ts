export const sleep = (seconds: number) =>
	new Promise((resolve, _) =>
		setTimeout(resolve, seconds * 1000)
	);

export const retrierFactory =
	(maxAttempts: number, delay: number) =>
	async (operation: () => any) =>
{
	for (let i = 0; i < maxAttempts; i++) {
		try {
			return await operation();
		} catch (ex) {
			await sleep(delay);
		}
	}

	throw new Error(`Retried operation failed`);
}
