import { expect, test } from 'vitest';
import { PaginatedState } from './paginated.svelte';
import type { Page } from '$lib/api/pagination';

test('a late response cannot replace a newer search', async () => {
	const list = new PaginatedState<string>();
	let finish!: (page: Page<string>) => void;
	const old = list.load(
		() =>
			new Promise((resolve) => {
				finish = resolve;
			})
	);
	await list.load(async () => ({ items: ['current'], total_count: 1 }));
	finish({ items: ['stale'], total_count: 51 });
	await old;
	expect(list.items).toEqual(['current']);
	expect(list.total).toBe(1);
	expect(list.loading).toBe(false);
});

test('a late failure cannot hide a successful newer page', async () => {
	const list = new PaginatedState<string>();
	let fail!: (error: Error) => void;
	const old = list.load(
		() =>
			new Promise((_, reject) => {
				fail = reject;
			})
	);
	await list.load(async () => ({ items: ['current'], total_count: 1 }));
	fail(new Error('offline'));
	await old;
	expect(list.error).toBe('');
	expect(list.items).toEqual(['current']);
});

test('deleting the last row returns to the last remaining page', async () => {
	const list = new PaginatedState<number>();
	const offsets: number[] = [];
	await list.load(async (offset) => {
		offsets.push(offset);
		return { items: offset === 100 ? [] : [51], total_count: 51 };
	}, 100);
	expect(offsets).toEqual([100, 50]);
	expect(list.offset).toBe(50);
	expect(list.items).toEqual([51]);
});

test('failure preserves data for retry and clears the error only after a new load', async () => {
	const list = new PaginatedState<number>();
	await list.load(async () => ({ items: [1], total_count: 1 }));
	await list.load(async () => {
		throw new Error('offline');
	});
	expect(list.items).toEqual([1]);
	expect(list.error).toContain('retry');
	expect(list.loading).toBe(false);
	await list.load(async () => ({ items: [], total_count: 0 }));
	expect(list.error).toBe('');
	expect(list.items).toEqual([]);
});
