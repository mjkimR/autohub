import { api } from '$lib/api';
import { session } from '$lib/stores/session.svelte';

/** Rows read per check; a larger backlog is shown as a lower bound ("50+"). */
export const PENDING_DECISION_SAMPLE = 50;
/** Background cadence while the tab is visible; navigation refreshes are throttled separately. */
export const PENDING_DECISION_POLL_MS = 60_000;
export const PENDING_DECISION_NAV_MIN_MS = 15_000;

/**
 * Operator-owed decisions across visible projects: the Decision inbox rows that carry
 * attention (actionable "Needs decision" and "Answer saved — resume pending").
 * `unknown` covers loading, errors and an undecidable sample, and is always shown neutral.
 */
export type PendingDecisionCount =
	{ status: 'unknown' } | { status: 'known'; count: number; lowerBound: boolean };

export function summarizePendingDecisions(page: {
	items: { actionable: boolean }[];
	has_more: boolean;
}): PendingDecisionCount {
	const count = page.items.filter((item) => item.actionable).length;
	// More rows exist but none in the sample are owed: the total is not knowable from this page.
	if (page.has_more && count === 0) return { status: 'unknown' };
	return { status: 'known', count, lowerBound: page.has_more };
}

/** Visible count text, e.g. "3" or "50+"; empty when nothing is owed or the count is unknown. */
export function pendingDecisionText(value: PendingDecisionCount): string {
	if (value.status !== 'known' || value.count === 0) return '';
	return `${value.count}${value.lowerBound ? '+' : ''}`;
}

/** Screen-reader phrase, e.g. "3 pending decisions" or "50 or more pending decisions". */
export function pendingDecisionPhrase(value: PendingDecisionCount): string {
	const text = pendingDecisionText(value);
	if (!text || value.status !== 'known') return '';
	const noun = value.count === 1 && !value.lowerBound ? 'decision' : 'decisions';
	return `${value.count}${value.lowerBound ? ' or more' : ''} pending ${noun}`;
}

/** Shell signal source: one bounded inbox read per minute while visible, plus throttled navigation refreshes. */
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
				params: { query: { limit: PENDING_DECISION_SAMPLE } }
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
