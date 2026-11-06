import type { components } from '$lib/api';

export type MilestonePreview = components['schemas']['MilestonePreview'];
export type MilestoneMember = components['schemas']['MilestoneMember'];

/** Only eligible direct members of a complete observation can enter the local review. */
export function orderedSelection(
	preview: MilestonePreview | null,
	selected: string[]
): MilestoneMember[] {
	if (!preview?.complete) return [];
	const members = preview.members.filter(
		(member) => member.eligibility === 'eligible_now' && selected.includes(member.id)
	);
	const remaining = new Map(members.map((member) => [member.id, member]));
	const result: MilestoneMember[] = [];
	while (remaining.size) {
		const next = [...remaining.keys()]
			.sort()
			.find(
				(id) =>
					!preview.edges.some(
						(edge) => edge.source === id && remaining.has(String(edge.canonical_id))
					)
			);
		if (!next) return [];
		result.push(remaining.get(next)!);
		remaining.delete(next);
	}
	return result;
}
