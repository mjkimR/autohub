import { expect, test, vi } from 'vitest';
import { allPages, responseData } from './pagination';

test('option lists include the 101st item', async () => {
	const rows = Array.from({ length: 101 }, (_, id) => ({ id }));
	const fetchPage = vi.fn(async (offset: number, limit: number) => ({
		items: rows.slice(offset, offset + limit),
		total_count: rows.length
	}));
	expect(await allPages(fetchPage)).toEqual(rows);
	expect(fetchPage.mock.calls).toEqual([
		[0, 100],
		[100, 100]
	]);
});

test('option lists with no total keep paging until the last short page', async () => {
	const rows = Array.from({ length: 101 }, (_, id) => id);
	expect(
		await allPages(async (offset, limit) => ({
			items: rows.slice(offset, offset + limit),
			total_count: null
		}))
	).toEqual(rows);
});

test('an interrupted option list fails instead of returning a partial success', async () => {
	const fetchPage = vi
		.fn()
		.mockResolvedValueOnce({ items: [1], total_count: 2 })
		.mockRejectedValueOnce(new Error('offline'));
	await expect(allPages(fetchPage)).rejects.toThrow('offline');
});

test('an inconsistent empty page cannot loop forever', async () => {
	await expect(allPages(async () => ({ items: [], total_count: 101 }))).rejects.toThrow('retry');
});

test('an HTTP failure is distinct from a successful empty list', () => {
	expect(responseData({ data: { items: [] } }, 'Failed')).toEqual({ items: [] });
	expect(() => responseData({ error: { detail: 'Unavailable' } }, 'Failed')).toThrow('Unavailable');
});
