import { api, type components } from '$lib/api';
import { apiErrorMessage } from '$lib/api/errors';
import type { OwedItem } from './owed-links';

/** The largest page the owed-item list accepts. */
export const OWED_PAGE_LIMIT = 100;

type Project = Pick<components['schemas']['ProjectRead'], 'id' | 'name'>;

/**
 * The landing's owed-item list: one keyset read per page in (`waiting_since`, `key`) order,
 * appended on Load more. A failed read keeps the last loaded items so nothing owed disappears.
 */
export class AttentionState {
	items = $state<OwedItem[]>([]);
	/** False until the first page for the current filter has loaded. */
	loaded = $state(false);
	loading = $state(false);
	loadingMore = $state(false);
	error = $state('');
	hasMore = $state(false);
	projectId = $state('');
	projects = $state<Project[]>([]);
	#cursor: string | null = null;
	#generation = 0;

	projectName(id: string): string | undefined {
		return this.projects.find((project) => project.id === id)?.name;
	}

	async loadProjects() {
		try {
			const { data } = await api.GET('/api/v1/projects', { params: { query: { limit: 100 } } });
			if (data) this.projects = data.items;
		} catch {
			// Names are a convenience: rows still link to their project without them.
		}
	}

	/** Reload the first page for the current filter. */
	async load() {
		const generation = ++this.#generation;
		this.loading = true;
		this.error = '';
		try {
			const page = await this.#read(null);
			if (generation !== this.#generation) return;
			this.items = page.items;
			this.hasMore = page.has_more;
			this.#cursor = page.next_cursor;
			this.loaded = true;
		} catch (e) {
			if (generation === this.#generation)
				this.error = apiErrorMessage(e, 'Owed items could not be loaded.');
		} finally {
			if (generation === this.#generation) this.loading = false;
		}
	}

	async loadMore() {
		if (!this.hasMore || !this.#cursor || this.loadingMore || this.loading) return;
		const generation = this.#generation;
		this.loadingMore = true;
		this.error = '';
		try {
			const page = await this.#read(this.#cursor);
			if (generation !== this.#generation) return;
			const seen = this.items.map((item) => item.key);
			this.items = [...this.items, ...page.items.filter((item) => !seen.includes(item.key))];
			this.hasMore = page.has_more;
			this.#cursor = page.next_cursor;
		} catch (e) {
			if (generation === this.#generation)
				this.error = apiErrorMessage(e, 'More owed items could not be loaded.');
		} finally {
			if (generation === this.#generation) this.loadingMore = false;
		}
	}

	setProject(projectId: string) {
		if (projectId === this.projectId) return;
		this.projectId = projectId;
		// A cursor is bound to its filters; a new filter starts from its first page.
		this.items = [];
		this.loaded = false;
		this.hasMore = false;
		this.#cursor = null;
		void this.load();
	}

	async #read(cursor: string | null) {
		const { data, error } = await api.GET('/api/v1/owed-items', {
			params: {
				query: {
					limit: OWED_PAGE_LIMIT,
					...(cursor ? { cursor } : {}),
					...(this.projectId ? { project_id: this.projectId } : {})
				}
			}
		});
		if (!data) throw error ?? new Error('Owed items could not be loaded.');
		return data;
	}
}
