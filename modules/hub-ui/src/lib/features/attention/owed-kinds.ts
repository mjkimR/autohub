import type { OwedItem, OwedKind } from './owed-links';

type KindPresentation = { kind: OwedKind; label: string; quiet: boolean };

/**
 * Landing order is by consequence: work stopped on an operator answer first, cleanup last.
 * Failed runs close the list as a quiet section: they carry no count weight (`CAP-PR-owed-items`).
 */
export const OWED_KINDS: readonly KindPresentation[] = [
	{ kind: 'decision', label: 'Decisions', quiet: false },
	{ kind: 'stopped-run', label: 'Held PR runs', quiet: false },
	{ kind: 'work-plan-proposed', label: 'Work Plans to review', quiet: false },
	{ kind: 'work-item-recovery', label: 'Work Item recovery', quiet: false },
	{ kind: 'work-item-replacement', label: 'Work Item replacement', quiet: false },
	{ kind: 'work-item-attention', label: 'Work Items needing attention', quiet: false },
	{ kind: 'sdd-batch-attention', label: 'SDD batches', quiet: false },
	{ kind: 'connection-test-cleanup', label: 'Connection-test cleanup', quiet: false },
	{ kind: 'failed-run', label: 'Failed PR runs', quiet: true }
];

export type OwedGroup = KindPresentation & { items: OwedItem[] };

/** Loaded items grouped in landing order; kinds with no loaded item are left out. */
export function groupOwedItems(items: readonly OwedItem[]): OwedGroup[] {
	return OWED_KINDS.map((entry) => ({
		...entry,
		items: items.filter((item) => item.kind === entry.kind)
	})).filter((group) => group.items.length > 0);
}

/** Compact waiting age, e.g. "12 min", "5 h", "3 d"; never negative. */
export function waitingAge(since: string, now: number = Date.now()): string {
	const minutes = Math.max(0, Math.floor((now - new Date(since).getTime()) / 60_000));
	if (minutes < 1) return 'under 1 min';
	if (minutes < 60) return `${minutes} min`;
	const hours = Math.floor(minutes / 60);
	if (hours < 48) return `${hours} h`;
	return `${Math.floor(hours / 24)} d`;
}

type CatalogHold = NonNullable<OwedItem['context']['catalog_hold']>;

/** Inline context for a run whose AI catalog is held; quiet text, never an owed item. */
export function catalogHoldText(hold: CatalogHold): string {
	const reason =
		hold.reason === 'quota-blocked' ? 'AI catalog quota is exhausted' : 'AI catalog is unavailable';
	if (!hold.available_at) return reason;
	const at = new Date(hold.available_at).toLocaleString([], {
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});
	return `${reason} until ${at}`;
}
