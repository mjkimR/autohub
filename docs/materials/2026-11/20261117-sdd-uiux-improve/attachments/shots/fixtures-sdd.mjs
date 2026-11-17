// SDD fixtures: repository documents, SDD runs, run questions/attempts, claims and start outcomes.
// Shapes follow modules/hub-ui/src/lib/api/generated/{sdd,pipeline-run,run-decisions,repository,common}.d.ts.
// Values are adapted from the *.integration.test.ts files beside the SDD components. No real data.

export const NOW = new Date('2026-11-12T09:30:00Z');
const ago = (min) => new Date(NOW.getTime() - min * 60_000).toISOString();
const later = (min) => new Date(NOW.getTime() + min * 60_000).toISOString();
const uuid = (n) => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`;
const stamps = (min) => ({ created_at: ago(min), updated_at: ago(Math.max(0, min - 5)) });

export const SDD_PROJECT = uuid(301);
const CAT_CODEX = uuid(201);
const REPO = 'example-org/payments-service';

export const PROP = 'docs/proposals/PROP-refund-idempotency';
export const PROP_EMPTY = 'docs/proposals/PROP-webhook-backoff';
export const SPEC = 'specs/2026-11/20261110-refund-idempotency';
export const CLAIM = uuid(950);

// ---- repository documents --------------------------------------------------
const docs = {
	'README.md': '# Payments service\n\nRefunds, settlements and ledger APIs for the example storefront.\n\n- `src/` service code\n- `docs/` capabilities, use cases and proposals\n- `specs/` delivery specs\n',
	'docs/README.md': '---\nid: DOC-index\ntitle: Documentation guide\nstatus: active\n---\n# Documentation guide\n\nCapabilities live in `capabilities/`, use cases in `usecases/` and proposals in `proposals/`.\n\nSee [Refunds capability](capabilities/CAP-refunds.md).\n',
	'docs/capabilities/CAP-refunds.md': '---\nid: CAP-refunds\ntitle: Refunds\nstatus: active\n---\n# Refunds\n\nThe service accepts partial and full refunds for settled payments.\n\n## Guarantees\n\n- A refund request with the same idempotency key returns the original result.\n- A refund never exceeds the captured amount.\n',
	'docs/usecases/UC-request-refund.md': '---\nid: UC-request-refund\ntitle: Request a refund\nstatus: active\n---\n# Request a refund\n\n**Actor:** storefront operator\n\nGiven a settled payment, when the operator requests a refund, then the ledger records one refund entry.\n',
	'docs/roadmap/MS-2026-q4.md': '---\nid: MS-2026-q4\ntitle: Q4 reliability\nstatus: active\ndepends_on: []\n---\n# Q4 reliability\n\nIdempotent refunds and resilient webhook delivery.\n',
	[`${PROP}/proposal.md`]: '---\nid: PROP-refund-idempotency\ntitle: Idempotent refund requests\nstatus: planning\nmilestone: MS-2026-q4\ntask_kind: feature\nplanning_effort: medium\ndev_effort: high\n---\n# Idempotent refund requests\n\n## Problem\n\nStorefront retries after a timeout can create duplicate refunds.\n\n## Intent\n\nAccept an `Idempotency-Key` header on `POST /refunds` and return the original result for a repeated key within 24 hours.\n\n## Non-goals\n\n- Changing settlement batching.\n- Idempotency for payment capture.\n\n## Open questions\n\n1. Should the key scope include the merchant account?\n2. Retention window: 24 hours or 7 days?\n',
	[`${PROP_EMPTY}/proposal.md`]: '---\nid: PROP-webhook-backoff\ntitle: Webhook delivery backoff\nstatus: draft\nmilestone: MS-2026-q4\ntask_kind: feature\n---\n# Webhook delivery backoff\n\nRetry failed webhook deliveries with exponential backoff and jitter.\n',
	[`${SPEC}/spec.md`]: '---\nid: SPEC-20261110-refund-idempotency\ntitle: Idempotent refund requests\nstatus: in-progress\nproposal: PROP-refund-idempotency\n---\n# Idempotent refund requests\n\n## Acceptance criteria\n\n- **Given** a refund request with key `K`, **when** the same request is repeated with `K`, **then** the original refund is returned and no ledger entry is added.\n- **Given** key `K` reused with a different body, **then** the service responds `422`.\n\n## Non-goals\n\n- Capture idempotency.\n',
	[`${SPEC}/plan.md`]: '# Plan\n\n1. Add `refund_idempotency_keys` table.\n2. Middleware reads `Idempotency-Key`.\n3. Store the response digest with the key.\n',
	[`${SPEC}/tasks.md`]: '# Tasks\n\n- [x] T1 Migration for idempotency keys\n- [ ] T2 Refund middleware\n- [ ] T3 Contract tests\n',
	'src/refunds/api.py': 'def create_refund(request):\n    ...\n'
};
const BRANCHES = ['main', 'autohub/plan-refund-idempotency', 'autohub/dev-refund-idempotency'];

function entriesFor() {
	const entries = new Map();
	for (const path of Object.keys(docs)) {
		const parts = path.split('/');
		parts.forEach((name, i) => {
			const parent = parts.slice(0, i).join('/');
			const child = parts.slice(0, i + 1).join('/');
			if (!entries.has(parent)) entries.set(parent, new Map());
			const file = i === parts.length - 1;
			entries.get(parent).set(child, { name, path: child, type: file ? 'file' : 'dir', size: file ? docs[path].length : 0, sha: `sha-${child.length}` });
		});
	}
	return entries;
}
const tree = entriesFor();

// ---- SDD runs --------------------------------------------------------------
const snap = (number, title, branch, sha) => ({
	number,
	url: `https://github.com/${REPO}/pull/${number}`,
	title,
	body: null,
	base_ref: 'main',
	head_ref: branch,
	head_sha: sha,
	linked_issues: []
});
const sddRun = (n, o) => ({
	id: uuid(n),
	project_id: SDD_PROJECT,
	ai_catalog_id: CAT_CODEX,
	requested_catalog_id: null,
	enrollment_source: 'native_sdd',
	related_origins: [],
	project_revision: 4,
	pull_number: o.pull,
	pull_url: `https://github.com/${REPO}/pull/${o.pull}`,
	pull_snapshot: snap(o.pull, o.title, o.branch, o.sha),
	pause_reason: null,
	branch: o.branch,
	revision: 6,
	epoch: 1,
	lease_owner: null,
	lease_expires_at: null,
	next_action_at: null,
	quota_block_count: 0,
	has_pending_decision: false,
	...stamps(o.age ?? 120),
	...o.extra
});
export const RUN_GATE = uuid(460);
export const RUN_RESUME = uuid(461);
export const RUN_IMPL = uuid(462);
export const RUN_FAILED = uuid(463);
export const RUN_DONE = uuid(464);
export const sddRuns = [
	sddRun(460, {
		pull: 431,
		title: 'Plan: Idempotent refund requests',
		branch: 'autohub/plan-refund-idempotency',
		sha: '4be0d5435ed84a1f9c2e7b3a6d0f1e2c3b4a5968',
		age: 180,
		extra: {
			state: 'paused',
			pause_reason: 'Planning gate: the agent asked for a decision before the plan is approved.',
			has_pending_decision: true,
			sdd_snapshot: { provider: 'repository-agent', spec_dir: PROP, activity_kind: 'plan', activity_effort: 'medium' },
			related_origins: [{ kind: 'native_sdd', id: CLAIM, unit: PROP, work_plan_id: null, catalog_id: null, url: null }]
		}
	}),
	sddRun(461, {
		pull: 433,
		title: 'Develop: Idempotent refund requests',
		branch: 'autohub/dev-refund-idempotency',
		sha: '9c2e7b3a6d0f1e2c3b4a59684be0d5435ed84a1f',
		age: 90,
		extra: {
			state: 'paused',
			pause_reason: 'Answer saved. The run stays stopped until an explicit resume.',
			has_pending_decision: true,
			revision: 9,
			sdd_snapshot: { provider: 'repository-agent', spec_dir: SPEC, handoff_from: PROP, activity_kind: 'dev', activity_effort: 'high' },
			related_origins: [{ kind: 'native_sdd', id: uuid(951), unit: PROP, work_plan_id: null, catalog_id: null, url: null }]
		}
	}),
	sddRun(462, {
		pull: 428,
		title: 'Develop: Refund ledger reconciliation report',
		branch: 'autohub/dev-ledger-report',
		sha: '1e2c3b4a59684be0d5435ed84a1f9c2e7b3a6d0f',
		age: 50,
		extra: {
			state: 'implementing',
			lease_owner: 'worker-1',
			lease_expires_at: later(12),
			sdd_snapshot: { provider: 'repository-agent', spec_dir: SPEC, activity_kind: 'dev', activity_effort: 'medium' },
			related_origins: [
				{ kind: 'native_sdd', id: uuid(952), unit: PROP, work_plan_id: null, catalog_id: null, url: null },
				{ kind: 'provider_session', id: 'sess-7f3a', catalog_id: CAT_CODEX, unit: null, work_plan_id: null, url: 'https://chatgpt.com/codex/tasks/sess-7f3a' }
			],
			enrollment_source: 'multiple'
		}
	}),
	sddRun(463, {
		pull: 421,
		title: 'Plan: Idempotent refund requests (first attempt)',
		branch: 'autohub/plan-refund-idempotency-1',
		sha: '6d0f1e2c3b4a59684be0d5435ed84a1f9c2e7b3a',
		age: 600,
		extra: {
			state: 'failed',
			pause_reason: 'Agent session ended without publishing a plan commit.',
			sdd_snapshot: { provider: 'repository-agent', spec_dir: PROP, activity_kind: 'plan', activity_effort: 'low' }
		}
	}),
	sddRun(464, {
		pull: 402,
		title: 'Plan: Refund API error catalog',
		branch: 'autohub/plan-refund-errors',
		sha: '3b4a59684be0d5435ed84a1f9c2e7b3a6d0f1e2c',
		age: 4000,
		extra: { state: 'completed', sdd_snapshot: { provider: 'repository-agent', spec_dir: 'docs/proposals/PROP-refund-error-catalog', activity_kind: 'plan' } }
	})
];
const runById = (id) => sddRuns.find((r) => r.id === id);

// ---- questions -------------------------------------------------------------
const q = (n, run, o) => ({
	id: uuid(n),
	pipeline_run_id: run.id,
	execution_attempt_id: uuid(n + 100),
	head_sha: run.pull_snapshot.head_sha,
	actor: 'agent',
	source: 'agent',
	resolution: null,
	answers: [],
	...o
});
const gate = runById(RUN_GATE);
const resumeRun = runById(RUN_RESUME);
const implRun = runById(RUN_IMPL);
export const questionsByRun = {
	[RUN_GATE]: [
		q(970, gate, {
			question: 'Planning gate: should the idempotency key scope include the merchant account, or stay global per API client?\n\nThe proposal leaves this open; the plan differs in the table key and migration.',
			state: 'open',
			created_at: ago(95)
		}),
		q(971, gate, {
			question: 'Use a 24 hour retention window for idempotency keys?',
			state: 'resolved',
			resolution: 'answered',
			created_at: ago(170),
			answers: [{ id: uuid(981), question_id: uuid(971), answer: 'Yes, 24 hours matches the storefront retry policy.', actor: 'demo@example.com', created_at: ago(160), applied_attempt_id: uuid(1071) }]
		})
	],
	[RUN_RESUME]: [
		q(972, resumeRun, {
			question: 'Development gate: tasks T2 and T3 touch the public refund contract. Continue with the contract change in this PR?',
			state: 'answered',
			created_at: ago(70),
			answers: [{ id: uuid(982), question_id: uuid(972), answer: 'Continue in this PR and add the contract tests from T3 first.', actor: 'demo@example.com', created_at: ago(40), applied_attempt_id: null }]
		})
	],
	[RUN_IMPL]: [
		q(973, implRun, {
			question: 'Reuse the existing ledger export job for the report?',
			state: 'resolved',
			resolution: 'answered',
			created_at: ago(45),
			answers: [{ id: uuid(983), question_id: uuid(973), answer: 'Yes, reuse it.', actor: 'demo@example.com', created_at: ago(42), applied_attempt_id: uuid(1073) }]
		})
	]
};

// ---- attempts --------------------------------------------------------------
const attempt = (n, run, o) => ({
	id: uuid(n),
	pipeline_run_id: run.id,
	attempt_number: 1,
	epoch: 1,
	kind: 'implementation',
	state: 'completed',
	request_snapshot: {},
	request_digest: 'f3a9c1d27be04e5a8c6d9e0f1a2b3c4d5e6f7a8b',
	idempotency_key: `${run.id.slice(-6)}-impl-${o.attempt_number ?? 1}`,
	external_correlation_id: 'codex-task-7f3a',
	external_status: 'completed',
	conversation_url: 'https://chatgpt.com/codex/tasks/sess-7f3a',
	started_at: ago(o.age ?? 60),
	finished_at: ago((o.age ?? 60) - 20),
	failure_code: null,
	failure_detail: null,
	...stamps(o.age ?? 60),
	...o
});
const summary = (o) => ({ attempts_by_kind: { implementation: 1 }, requests_sent: 2, quota_limit_replies: 0, started_at: ago(180), finished_at: null, elapsed_seconds: 10800, ...o });
const failedRun = runById(RUN_FAILED);
export const attemptsByRun = {
	[RUN_GATE]: { items: [attempt(1071, gate, { state: 'suspended', finished_at: null, age: 175 })], summary: summary({}) },
	[RUN_RESUME]: { items: [attempt(1072, resumeRun, { state: 'suspended', finished_at: null, age: 85 })], summary: summary({ elapsed_seconds: 5400, started_at: ago(90) }) },
	[RUN_IMPL]: {
		items: [
			attempt(1073, implRun, { state: 'running', finished_at: null, age: 48 }),
			attempt(1074, implRun, { attempt_number: 2, kind: 'ci-fix', state: 'planned', started_at: null, finished_at: null, age: 2, conversation_url: null })
		],
		summary: summary({ attempts_by_kind: { implementation: 1, 'ci-fix': 1 }, requests_sent: 3, elapsed_seconds: 2880, started_at: ago(48) })
	},
	[RUN_FAILED]: {
		items: [attempt(1075, failedRun, { state: 'failed', age: 590, failure_code: 'AGENT_NO_COMMIT', failure_detail: 'The agent session finished without pushing a plan commit to autohub/plan-refund-idempotency-1.' })],
		summary: summary({ finished_at: ago(560), elapsed_seconds: 1800, started_at: ago(590), quota_limit_replies: 1 })
	},
	[RUN_DONE]: { items: [], summary: summary({ attempts_by_kind: {}, requests_sent: 0, elapsed_seconds: 0 }) }
};

// ---- decisions inbox entries ----------------------------------------------
const entry = (run, question, o) => ({
	key: `run-question:${question.id}`,
	run_id: run.id,
	run_state: run.state,
	pull_number: run.pull_number,
	pull_url: run.pull_url,
	project_id: SDD_PROJECT,
	kind: 'run-question',
	subject_id: question.id,
	fingerprint: `fp-${question.id.slice(-4)}`,
	title: question.question.split('\n')[0],
	question_state: question.state,
	actionable: true,
	waiting_since: question.created_at,
	observed_at: ago(2),
	revision: run.revision,
	head_sha: run.pull_snapshot.head_sha,
	...o
});
export const sddDecisions = [entry(gate, questionsByRun[RUN_GATE][0], {}), entry(resumeRun, questionsByRun[RUN_RESUME][0], {})];

// ---- claims ----------------------------------------------------------------
export const claims = {
	releasable: { id: CLAIM, project_id: SDD_PROJECT, unit: PROP, activity: 'plan', run_id: null, settled: false, checkpoint_digest: 'reviewed-digest', checkpoint: { pull_number: 431, uncertain: true, lease_expires_at: ago(30) } },
	live: { id: CLAIM, project_id: SDD_PROJECT, unit: PROP, activity: 'plan', run_id: null, settled: false, checkpoint_digest: 'reviewed-digest', checkpoint: { uncertain: true, lease_expires_at: later(10) } },
	withRun: { id: CLAIM, project_id: SDD_PROJECT, unit: PROP, activity: 'plan', run_id: RUN_GATE, settled: false, checkpoint_digest: 'reviewed-digest', checkpoint: { pull_number: 431, uncertain: false } },
	settled: { id: CLAIM, project_id: SDD_PROJECT, unit: PROP, activity: 'plan', run_id: RUN_GATE, settled: true, checkpoint_digest: 'reviewed-digest', checkpoint: { pull_number: 431 } }
};

// Start outcomes for POST planning/development/runs, chosen per shot by scenario.start.
const problem = (status, detail, code) => ({ status, body: { type: 'about:blank', title: 'Project Error', status, detail, code } });
const startOutcomes = {
	success: () => ({ status: 201, body: { ...gate, id: uuid(465), state: 'queued', pause_reason: null, has_pending_decision: false } }),
	refused: () => problem(422, 'Enable the project and connect its GitHub repository', 'INVALID_REQUEST'),
	'base-missing': () => problem(422, 'Base branch release/2026-q4 is not on the remote', 'INVALID_REQUEST'),
	unresolved: () => problem(503, 'GitHub publication outcome is unknown; retry the same request', 'UPSTREAM_ERROR'),
	conflict: () => problem(409, `Activity has unsettled owner claim ${CLAIM}; inspect /api/v1/projects/${SDD_PROJECT}/sdd/claims/${CLAIM}`, 'SDD_ACTIVITY_OWNED'),
	'conflict-no-claim': () => problem(409, 'Activity branch has a different owner or head', 'SDD_BRANCH_EXISTS'),
	'enroll-reconcile': () => problem(409, `Activity claim ${CLAIM} retains external work; inspect /api/v1/projects/${SDD_PROJECT}/sdd/claims/${CLAIM} and explicitly reconcile uncertainty before replacement`, 'SDD_RECONCILIATION_REQUIRED')
};

/**
 * SDD routes. Returns { status, body } or null (falls through to the base fixtures).
 * scenario: per-shot options, e.g. { start: 'conflict', claim: 'live', sddRuns: 'empty' }.
 */
export function handleSdd(method, path, q, body, scenario = {}) {
	let m;
	// Needs-you counts (sidebar badge and the project exception strip)
	if (method === 'GET' && path === '/api/v1/owed-items/counts') {
		const pid = q.get('project_id');
		if (pid && pid !== SDD_PROJECT) return { status: 200, body: { total: 0, by_kind: {}, by_project: {} } };
		return { status: 200, body: { total: 3, by_kind: { decision: 2, 'stopped-run': 1, 'failed-run': 1 }, by_project: { [SDD_PROJECT]: 3 } } };
	}
	// repository
	if ((m = path.match(/^\/api\/v1\/projects\/([^/]+)\/repository\/(info|tree|blob)$/))) {
		if (m[1] !== SDD_PROJECT) return null;
		if (m[2] === 'info') return { status: 200, body: { repository: REPO, default_branch: 'main', branches_complete: true, branches: BRANCHES } };
		const p = q.get('path') ?? '';
		const ref = q.get('ref') ?? 'main';
		if (m[2] === 'tree') {
			if (!tree.has(p)) return { status: 404, body: { detail: `Path ${p} not found on ${ref}` } };
			return { status: 200, body: { path: p, ref, items: [...tree.get(p).values()] } };
		}
		if (!(p in docs)) return { status: 404, body: { detail: `File ${p} not found on ${ref}` } };
		return { status: 200, body: { path: p, ref, size: docs[p].length, sha: `sha-${p.length}`, encoding: 'utf-8', content: docs[p] } };
	}
	// SDD runs for a unit
	if ((m = path.match(/^\/api\/v1\/projects\/([^/]+)\/sdd\/runs$/))) {
		const spec = q.get('spec_dir') ?? '';
		if (scenario.sddRuns === 'empty' || spec === PROP_EMPTY) return { status: 200, body: [] };
		return { status: 200, body: sddRuns.filter((r) => r.sdd_snapshot?.spec_dir === spec || r.sdd_snapshot?.handoff_from === spec || (spec === PROP && r.related_origins.some((o) => o.unit === PROP))) };
	}
	if ((m = path.match(/^\/api\/v1\/projects\/([^/]+)\/sdd\/proposals\/([^/]+)\/(planning|development)$/)) && method === 'POST')
		return startOutcomes[scenario.start ?? 'success']();
	if ((m = path.match(/^\/api\/v1\/projects\/([^/]+)\/runs$/)) && method === 'POST') return startOutcomes[scenario.start ?? 'success']();
	if ((m = path.match(/^\/api\/v1\/projects\/([^/]+)\/sdd\/claims\/([^/]+)$/))) return { status: 200, body: claims[scenario.claim ?? 'releasable'] };
	if ((m = path.match(/^\/api\/v1\/projects\/([^/]+)\/sdd\/claims\/([^/]+)\/reconcile$/))) return { status: 200, body: claims.settled };
	// runs
	if ((m = path.match(/^\/api\/v1\/pipeline-runs\/([^/]+)$/)) && runById(m[1])) return { status: 200, body: runById(m[1]) };
	if ((m = path.match(/^\/api\/v1\/pipeline-runs\/([^/]+)\/questions$/))) {
		const run = runById(m[1]);
		const items = run ? (questionsByRun[run.id] ?? []) : [];
		return { status: 200, body: { items, total_count: items.length, run_revision: run?.revision ?? 1 } };
	}
	if ((m = path.match(/^\/api\/v1\/pipeline-runs\/([^/]+)\/questions\/([^/]+)$/))) {
		const item = (questionsByRun[m[1]] ?? []).find((x) => x.id === m[2]);
		return item ? { status: 200, body: item } : { status: 404, body: { detail: 'Question not found' } };
	}
	if ((m = path.match(/^\/api\/v1\/pipeline-runs\/([^/]+)\/attempts$/))) {
		const a = attemptsByRun[m[1]];
		if (!a) return null;
		return { status: 200, body: { items: a.items, total_count: a.items.length, summary: a.summary } };
	}
	if (method === 'POST' && path === '/api/v1/pipeline-runs/decisions/review') {
		const e = sddDecisions.find((d) => d.key === body?.key);
		return e ? { status: 200, body: runById(e.run_id) } : null;
	}
	return null;
}
