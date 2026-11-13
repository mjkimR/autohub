import { getContext, setContext } from 'svelte';
import { api, type components } from '$lib/api';
import { apiErrorMessage } from '$lib/api/errors';
import { session } from '$lib/stores/session.svelte';
import type { OwedKind } from './owed-links';

/** Background cadence while the tab is visible; navigation refreshes are throttled separately. */
export const OWED_COUNTS_POLL_MS = 60_000;
export const OWED_COUNTS_NAV_MIN_MS = 15_000;

type Counts = components['schemas']['OwedItemCounts'];

/**
 * The counted owed items across visible projects (`CAP-PR-owed-items`). `unknown` covers loading,
 * errors and invalid responses; it is shown as a neutral "?" so an outage never reads as zero or debt.
 */
export type OwedCounts =
	| { status: 'unknown' }
	| {
			status: 'known';
			total: number;
			byKind: Partial<Record<OwedKind, number>>;
			byProject: Record<string, number>;
	  };

const validCount = (value: unknown): value is number =>
	typeof value === 'number' && Number.isInteger(value) && value >= 0;

export function summarizeOwedCounts(data: Partial<Counts> | undefined): OwedCounts {
	if (!data || !validCount(data.total)) return { status: 'unknown' };
	const pick = (source: Record<string, number> | undefined) =>
		Object.fromEntries(Object.entries(source ?? {}).filter(([, value]) => validCount(value)));
	return {
		status: 'known',
		total: data.total,
		byKind: pick(data.by_kind),
		byProject: pick(data.by_project)
	};
}

/** Visible count text, e.g. "3"; empty when nothing is owed or the count is unknown. */
export function owedText(value: OwedCounts): string {
	return value.status === 'known' && value.total > 0 ? String(value.total) : '';
}

/** Screen-reader phrase, e.g. "3 items need you" or "1 item needs you". */
export function owedPhrase(value: OwedCounts): string {
	if (value.status !== 'known' || value.total === 0) return '';
	return value.total === 1 ? '1 item needs you' : `${value.total} items need you`;
}

/** Decision part of the same response, for the Decisions link; empty when zero or unknown. */
export function decisionText(value: OwedCounts): string {
	const count = value.status === 'known' ? (value.byKind.decision ?? 0) : 0;
	return count > 0 ? String(count) : '';
}

export function decisionPhrase(value: OwedCounts): string {
	const count = value.status === 'known' ? (value.byKind.decision ?? 0) : 0;
	if (count === 0) return '';
	return `${count} pending ${count === 1 ? 'decision' : 'decisions'}`;
}

/** Accessible name and tooltip of the neutral "?" mark shown while the count is unknown. */
export const OWED_UNKNOWN_LABEL = 'Owed items unknown';

/**
 * Shell signal source: one counts read per minute while visible, plus throttled navigation
 * refreshes. The shell shares its instance through context so the Attention landing reuses the
 * same response instead of adding a read.
 */
export class OwedCountsStore {
	value = $state<OwedCounts>({ status: 'unknown' });
	error = $state('');
	#checkedAt = 0;
	#inflight = false;

	async refresh() {
		if (this.#inflight) return;
		this.#inflight = true;
		this.#checkedAt = Date.now();
		const generation = session.generation;
		let next: OwedCounts = { status: 'unknown' };
		const fallback = 'Needs-you counts are unavailable';
		let error = '';
		try {
			const response = await api.GET('/api/v1/owed-items/counts');
			if (response.error) error = apiErrorMessage(response.error, fallback);
			else {
				next = summarizeOwedCounts(response.data);
				if (next.status === 'unknown') error = fallback;
			}
		} catch {
			error = fallback;
		} finally {
			this.#inflight = false;
		}
		if (generation === session.generation) {
			this.value = next;
			this.error = error;
		}
	}

	/** Refresh unless a check started within `minMs`; hidden tabs never poll. */
	refreshIfStale(minMs: number) {
		if (typeof document !== 'undefined' && document.hidden) return;
		if (Date.now() - this.#checkedAt < minMs) return;
		void this.refresh();
	}

	start(): () => void {
		void this.refresh();
		const interval = setInterval(
			() => this.refreshIfStale(OWED_COUNTS_POLL_MS - 1000),
			OWED_COUNTS_POLL_MS
		);
		const onVisible = () => this.refreshIfStale(OWED_COUNTS_POLL_MS);
		document.addEventListener('visibilitychange', onVisible);
		return () => {
			clearInterval(interval);
			document.removeEventListener('visibilitychange', onVisible);
		};
	}
}

export const OWED_COUNTS_CONTEXT = Symbol('owed-counts');

export function provideOwedCounts(store: OwedCountsStore): OwedCountsStore {
	return setContext(OWED_COUNTS_CONTEXT, store);
}

/** The shell's counts store, or undefined outside the shell (for example in isolated tests). */
export function useOwedCounts(): OwedCountsStore | undefined {
	return getContext<OwedCountsStore | undefined>(OWED_COUNTS_CONTEXT);
}
