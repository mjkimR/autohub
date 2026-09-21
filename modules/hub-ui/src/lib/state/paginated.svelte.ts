import type { Page } from '$lib/api/pagination';

/** A page is replaced only by the latest request, including errors and loading state. */
export class PaginatedState<T> {
	items = $state<T[]>([]);
	total = $state(0);
	offset = $state(0);
	loading = $state(true);
	error = $state('');
	readonly limit = 50;
	private generation = 0;

	async load(fetchPage: (offset: number, limit: number) => Promise<Page<T>>, offset = this.offset) {
		const generation = ++this.generation;
		this.offset = offset;
		this.loading = true;
		this.error = '';
		try {
			let page = await fetchPage(offset, this.limit);
			// Deleting the last row on a page returns to the last remaining page.
			if (offset > 0 && offset >= page.total_count) {
				offset = Math.max(0, Math.ceil(page.total_count / this.limit) - 1) * this.limit;
				page = await fetchPage(offset, this.limit);
			}
			if (generation !== this.generation) return;
			this.items = page.items;
			this.total = page.total_count;
			this.offset = offset;
		} catch {
			if (generation === this.generation) this.error = 'Failed to load this list. Please retry.';
		} finally {
			if (generation === this.generation) this.loading = false;
		}
	}
}
