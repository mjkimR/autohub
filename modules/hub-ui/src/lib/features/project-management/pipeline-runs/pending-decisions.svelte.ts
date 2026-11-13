import { api } from '$lib/api';
import { session } from '$lib/stores/session.svelte';

/** Background cadence while the tab is visible; navigation refreshes are throttled separately. */
export const PENDING_DECISION_POLL_MS = 60_000;
export const PENDING_DECISION_NAV_MIN_MS = 15_000;

/**
 * Operator-owed decisions across visible projects: the Decision inbox rows that carry
 * attention (actionable "Needs decision" and "Answer saved — resume pending"), counted
 * exactly by the backend. `unknown` covers loading and errors and is always shown neutral.
 */
export type PendingDecisionCount = { status: 'unknown' } | { status: 'known'; count: number };

export function summarizePendingDecisions(page: {
	actionable_total_count?: number;
}): PendingDecisionCount {
	const count = page.actionable_total_count;
	// A response without a valid count (e.g. an older backend) must not look like operator debt.
	if (count === undefined || !Number.isInteger(count) || count < 0) {
		return { status: 'unknown' };
	}
	return { status: 'known', count };
}

/** Visible count text, e.g. "3"; empty when nothing is owed or the count is unknown. */
export function pendingDecisionText(value: PendingDecisionCount): string {
	if (value.status !== 'known' || value.count === 0) return '';
	return String(value.count);
}

/** Screen-reader phrase, e.g. "3 pending decisions" or "1 pending decision". */
export function pendingDecisionPhrase(value: PendingDecisionCount): string {
	if (value.status !== 'known' || value.count === 0) return '';
	return `${value.count} pending ${value.count === 1 ? 'decision' : 'decisions'}`;
}

/** Shell signal source: one minimal inbox read per minute while visible, plus throttled navigation refreshes. */
export class PendingDecisions {
	value = $state<PendingDecisionCount>({ status: 'unknown' });
	#checkedAt = 0;
	#inflight = false;

	async refresh() {
		if (this.#inflight) return;
		this.#inflight = true;
		this.#checkedAt = Date.now();
		const generation = session.generation;
		let next: PendingDecisionCount = { status: 'unknown' };
		try {
			const { data } = await api.GET('/api/v1/pipeline-runs/decisions', {
				// The count covers every row; one item is the smallest page the list accepts.
				params: { query: { limit: 1 } }
			});
			if (data) next = summarizePendingDecisions(data);
		} catch {
			// Failure stays neutral: an outage must never look like operator debt.
		} finally {
			this.#inflight = false;
		}
		if (generation === session.generation) this.value = next;
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
			() => this.refreshIfStale(PENDING_DECISION_POLL_MS - 1000),
			PENDING_DECISION_POLL_MS
		);
		const onVisible = () => this.refreshIfStale(PENDING_DECISION_POLL_MS);
		document.addEventListener('visibilitychange', onVisible);
		return () => {
			clearInterval(interval);
			document.removeEventListener('visibilitychange', onVisible);
		};
	}
}
