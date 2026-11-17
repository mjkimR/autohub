import type { components } from '$lib/api';
import { isTerminalRun } from '../../pipeline-runs/run-actions';
import { latestRunsByActivity, runOwesOperator, type UnitActivity } from '../sdd-unit';
import { isProposalPath, isSpecAnchorPath, milestoneRows } from './discovery';
import type { RepositoryDocument } from './model';

type Run = components['schemas']['PipelineRunRead'];

export type ProgressRow = {
	document: RepositoryDocument;
	/** The unit directory, as PR runs record it in `sdd_snapshot.spec_dir`. */
	unit: string;
	runs: { activity: UnitActivity | null; run: Run }[];
};
export type ProgressGroup = {
	key: string;
	title: string;
	/** The milestone document, for milestone groups. */
	milestone?: RepositoryDocument;
	dependencies: { id: string; status: string }[];
	rows: ProgressRow[];
};

const unitOf = (path: string) => path.split('/').slice(0, -1).join('/');

/** PR runs grouped by the unit they were requested for, newest first as listed. */
export function runsByUnit(runs: Run[]): Map<string, Run[]> {
	const byUnit = new Map<string, Run[]>();
	for (const run of runs) {
		const unit = run.sdd_snapshot?.spec_dir;
		if (typeof unit === 'string' && unit) byUnit.set(unit, [...(byUnit.get(unit) ?? []), run]);
	}
	return byUnit;
}

/**
 * Units on the branch with their latest PR run per activity: milestone members first (direct
 * proposal anchors only, CAP-DOC-repository-viewer), then other proposals, then specs newest
 * first. Groups follow document order; nothing here ranks readiness or what to start next.
 */
export function progressGroups(
	documents: RepositoryDocument[],
	runs: Map<string, Run[]> = new Map()
): ProgressGroup[] {
	const row = (document: RepositoryDocument): ProgressRow => {
		const unit = unitOf(document.path);
		return { document, unit, runs: latestRunsByActivity(runs.get(unit) ?? []) };
	};
	const milestones = milestoneRows(documents);
	const members = new Set(milestones.flatMap((m) => m.members.map((doc) => doc.path)));
	const groups: ProgressGroup[] = milestones.map((m) => ({
		key: m.document.path,
		title: m.document.title,
		milestone: m.document,
		dependencies: m.dependencies,
		rows: m.members.map(row)
	}));
	const loose = documents.filter(
		(doc) => isProposalPath(doc.path) && !members.has(doc.path) && doc.status !== 'rejected'
	);
	if (loose.length)
		groups.push({
			key: 'proposals',
			title: milestones.length ? 'Proposals outside milestones' : 'Proposals',
			dependencies: [],
			rows: loose.map(row)
		});
	const specs = documents
		.filter((doc) => isSpecAnchorPath(doc.path))
		.sort((a, b) => b.path.localeCompare(a.path));
	if (specs.length)
		groups.push({ key: 'specs', title: 'Specs', dependencies: [], rows: specs.map(row) });
	return groups;
}

/** Descriptive counts for a group heading; not a completion or readiness measure. */
export function groupSummary(rows: ProgressRow[]): string {
	const runs = rows.flatMap((row) => row.runs.map((entry) => entry.run));
	const active = rows.filter((row) => row.runs.some(({ run }) => !isTerminalRun(run))).length;
	const owed = runs.filter(runOwesOperator).length;
	const parts = [`${rows.length} ${rows.length === 1 ? 'unit' : 'units'}`];
	if (active) parts.push(`${active} with an active PR run`);
	if (owed) parts.push(`${owed} waiting on you`);
	return parts.join(' · ');
}
