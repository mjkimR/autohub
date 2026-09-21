import { apiErrorMessage } from './errors';

export type Page<T> = { items: T[]; total_count: number };

export function responseData<T>(result: { data?: T; error?: unknown }, fallback: string): T {
	if (result.error || result.data === undefined)
		throw new Error(apiErrorMessage(result.error, fallback));
	return result.data;
}

/** Load complete option lists; history tables should use pages instead. */
export async function allPages<T>(
	fetchPage: (offset: number, limit: number) => Promise<{ items: T[]; total_count?: number | null }>
): Promise<T[]> {
	const items: T[] = [];
	let total: number;
	do {
		const page = await fetchPage(items.length, 100);
		total =
			page.total_count ?? (page.items.length < 100 ? items.length + page.items.length : Infinity);
		if (page.items.length === 0 && items.length < total)
			throw new Error('The list changed; retry loading it');
		items.push(...page.items);
	} while (items.length < total);
	return items;
}
