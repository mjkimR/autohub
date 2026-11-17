import {
	Ban,
	CircleCheck,
	Clock,
	GitPullRequest,
	GitPullRequestClosed,
	GitPullRequestDraft,
	OctagonX
} from '@lucide/svelte';
import type { components } from '$lib/api';
import { displayLabel } from '$lib/labels';
import type { RunStatePresentation } from './presentation';

type Run = components['schemas']['PipelineRunRead'];
export type PullObservation = NonNullable<Run['pull_observation']>;
type Verification = PullObservation['verification'];

/** Display labels; written out so "CI" and "PR" keep their case. */
const VERIFICATION_LABELS: Record<Verification, string> = {
	waiting: 'CI waiting',
	failed: 'CI failed',
	blocked: 'CI blocked',
	passed: 'CI passed',
	closed: 'PR closed'
};

/**
 * Observed CI verification → badge. Failed checks are failed work (`destructive`); the rest are
 * routine signals in quiet roles (docs/steering/visual-style.md). A verification alone is never
 * operator debt, so it never takes `attention`.
 */
export function verificationPresentation(value: Verification): RunStatePresentation {
	const label = displayLabel(value, VERIFICATION_LABELS);
	switch (value) {
		case 'passed':
			return { variant: 'success', icon: CircleCheck, label };
		case 'failed':
			return { variant: 'destructive', icon: OctagonX, label };
		case 'blocked':
			return { variant: 'warning', icon: Ban, label };
		case 'closed':
			return { variant: 'secondary', icon: GitPullRequestClosed, label };
		default:
			return { variant: 'outline', icon: Clock, label };
	}
}

/** Observed Draft status → neutral badge; marking Ready is the operator's step in GitHub. */
export function draftPresentation(draft: boolean): RunStatePresentation {
	return draft
		? { variant: 'outline', icon: GitPullRequestDraft, label: 'Draft' }
		: { variant: 'outline', icon: GitPullRequest, label: 'Ready for review' };
}

/** A head Hub saw after the observation, such as a Run question bound to a newer push. */
export type LaterHead = { head_sha: string; at: string };

/**
 * The newest head known to be newer than the observation, or null when the observation is the
 * latest head evidence on hand. The run read carries no current head (`pull_snapshot.head_sha` is
 * the enrollment head), so only later evidence can mark an observation as stale.
 */
export function newerHead(observation: PullObservation, later: LaterHead[]): string | null {
	const observedAt = Date.parse(observation.observed_at);
	const newer = later
		.filter((head) => head.head_sha && Date.parse(head.at) > observedAt)
		.sort((a, b) => Date.parse(b.at) - Date.parse(a.at))[0];
	return newer && newer.head_sha !== observation.head_sha ? newer.head_sha : null;
}
