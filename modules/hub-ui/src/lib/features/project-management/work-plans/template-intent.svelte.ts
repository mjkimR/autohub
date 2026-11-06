import { api, type components } from '$lib/api';
import { apiErrorMessage } from '$lib/api/errors';

type S = components['schemas'];
export type Template = S['WorkPlanTemplateRead'];
export type Outcome = S['TemplateOutcome'];
export type Pending = {
	op: 'create' | 'from-plan' | 'update' | 'delete' | 'register';
	target: string | null;
	body:
		| S['TemplateCreate']
		| S['TemplateUpdate']
		| S['TemplateDelete']
		| S['TemplateFromPlan']
		| S['TemplateRegistration'];
};
export const storagePrefix = 'work-plan-template-intent:';
export class TemplateIntent {
	pending = $state<Pending | null>(null);
	outcome = $state<Outcome | null>(null);
	state = $state<'idle' | 'unknown' | 'recorded' | 'refused'>('idle');
	busy = $state(false);
	error = $state('');
	storageError = $state(false);
	constructor(
		readonly project: string,
		readonly account: string
	) {
		try {
			const saved = sessionStorage.getItem(this.key);
			if (saved) {
				const value = JSON.parse(saved);
				if (
					!value ||
					!['create', 'from-plan', 'update', 'delete', 'register'].includes(value.op) ||
					!value.body?.request_id
				)
					throw new Error('Invalid saved request');
				this.pending = value;
				this.state = 'unknown';
			}
		} catch {
			this.storageError = true;
			this.error =
				'Saved request cannot be restored. Reopen the original request history; do not substitute a new request.';
		}
	}
	get key() {
		return storagePrefix + this.account + ':' + this.project;
	}
	get locked() {
		return this.state === 'unknown' || this.busy || this.storageError;
	}
	remember() {
		sessionStorage.setItem(this.key, JSON.stringify(this.pending));
	}
	async submit(pending: Pending) {
		if (this.locked) throw new Error('Resolve the original template request first');
		this.outcome = null;
		this.error = '';
		this.pending = JSON.parse(JSON.stringify(pending));
		try {
			this.remember();
		} catch {
			this.storageError = true;
			this.error = 'Browser session storage is unavailable; request was not sent.';
			return;
		}
		this.state = 'unknown';
		await this.retry();
	}
	async retry() {
		const p = this.pending;
		if (!p || this.state !== 'unknown' || this.busy) return;
		this.busy = true;
		this.error = '';
		try {
			const path = { project_id: this.project, template_id: p.target ?? '' };
			let result;
			if (p.op === 'create')
				result = await api.POST('/api/v1/projects/{project_id}/work-plan-templates', {
					params: { path },
					body: p.body as S['TemplateCreate']
				});
			else if (p.op === 'from-plan')
				result = await api.POST('/api/v1/projects/{project_id}/work-plan-templates/from-plan', {
					params: { path },
					body: p.body as S['TemplateFromPlan']
				});
			else if (p.op === 'update')
				result = await api.PUT('/api/v1/projects/{project_id}/work-plan-templates/{template_id}', {
					params: { path },
					body: p.body as S['TemplateUpdate']
				});
			else if (p.op === 'delete')
				result = await api.DELETE(
					'/api/v1/projects/{project_id}/work-plan-templates/{template_id}',
					{ params: { path }, body: p.body as S['TemplateDelete'] }
				);
			else
				result = await api.POST(
					'/api/v1/projects/{project_id}/work-plan-templates/{template_id}/registrations',
					{ params: { path }, body: p.body as S['TemplateRegistration'] }
				);
			if (result.data) {
				this.record(result.data);
				return;
			}
			const error = result.error as { code?: string; detail?: unknown };
			const validation =
				result.response.status === 422 &&
				Array.isArray(error?.detail) &&
				error.detail.every(
					(item: { loc?: unknown[]; type?: unknown }) =>
						Array.isArray(item.loc) && typeof item.type === 'string'
				);
			if (
				validation ||
				[
					'TEMPLATE_REVISION_CHANGED',
					'TEMPLATE_BINDING_CHANGED',
					'TEMPLATE_SOURCE_CHANGED',
					'TEMPLATE_UNAVAILABLE',
					'TEMPLATE_REFUSED'
				].includes(error?.code ?? '')
			)
				this.state = 'refused';
			this.error = apiErrorMessage(result.error, 'Outcome unknown. Check the original request.');
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Outcome unknown';
		} finally {
			this.busy = false;
		}
	}
	async check() {
		const p = this.pending;
		if (!p || this.busy) return;
		this.busy = true;
		this.error = '';
		try {
			const result =
				p.op === 'register'
					? await api.GET(
							'/api/v1/projects/{project_id}/work-plan-templates/registrations/{request_id}',
							{ params: { path: { project_id: this.project, request_id: p.body.request_id } } }
						)
					: await api.GET(
							'/api/v1/projects/{project_id}/work-plan-templates/requests/{operation}/{request_id}',
							{
								params: {
									path: { project_id: this.project, operation: p.op, request_id: p.body.request_id }
								}
							}
						);
			if (!result.data)
				throw new Error(apiErrorMessage(result.error, 'Could not check original request'));
			if (result.data.record_state === 'recorded') this.record(result.data);
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Could not check original request';
		} finally {
			this.busy = false;
		}
	}
	record(outcome: Outcome) {
		this.outcome = outcome;
		this.state = 'recorded';
	}
	dismiss() {
		if (this.locked) return;
		sessionStorage.removeItem(this.key);
		this.pending = null;
		this.outcome = null;
		this.state = 'idle';
		this.error = '';
	}
}

export function freshPreview(
	template: Template,
	request = crypto.randomUUID()
): S['WorkPlanCreate'] {
	const slots = [...(template.definition.items ?? [])].sort((a, b) =>
		a.key < b.key ? -1 : a.key > b.key ? 1 : 0
	);
	const keys = Object.fromEntries(
		slots.map((item, index) => [
			item.key,
			`${item.key.slice(0, 22)}-${String(index).padStart(4, '0')}-${request.replaceAll('-', '')}`
		])
	);
	return {
		...template.definition,
		state: 'draft',
		group_key: null,
		scheduled_at: null,
		depends_on: [],
		request_id: request,
		items: slots.map((item) => ({
			...item,
			key: keys[item.key],
			depends_on: (item.depends_on ?? []).map((key) => keys[key])
		}))
	};
}
