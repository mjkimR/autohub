import { expect, test } from 'vitest';
import { draftPresentation, newerHead, verificationPresentation } from './pull-status';

const observation = {
	head_sha: 'a'.repeat(40),
	draft: true,
	verification: 'waiting' as const,
	reason: 'Waiting for checks',
	observed_at: '2026-11-12T09:00:00Z'
};

test('maps verification to display labels and quiet or failure roles, never attention', () => {
	expect(verificationPresentation('passed')).toMatchObject({
		label: 'CI passed',
		variant: 'success'
	});
	expect(verificationPresentation('failed')).toMatchObject({
		label: 'CI failed',
		variant: 'destructive'
	});
	expect(verificationPresentation('blocked').variant).toBe('warning');
	expect(verificationPresentation('closed').label).toBe('PR closed');
	expect(verificationPresentation('waiting').label).toBe('CI waiting');
	expect(draftPresentation(false).label).toBe('Ready for review');
});

test('flags only a different head seen after the observation', () => {
	expect(newerHead(observation, [])).toBeNull();
	expect(
		newerHead(observation, [{ head_sha: 'b'.repeat(40), at: '2026-11-12T08:00:00Z' }])
	).toBeNull();
	expect(
		newerHead(observation, [{ head_sha: 'a'.repeat(40), at: '2026-11-12T10:00:00Z' }])
	).toBeNull();
	expect(newerHead(observation, [{ head_sha: 'b'.repeat(40), at: '2026-11-12T10:00:00Z' }])).toBe(
		'b'.repeat(40)
	);
});
