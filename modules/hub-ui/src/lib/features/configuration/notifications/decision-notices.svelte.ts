import { SvelteMap } from 'svelte/reactivity';
import { session } from '$lib/stores/session.svelte';
import { api, type components } from '$lib/api';

type Read = components['schemas']['SubscriptionRead'];
type Write = components['schemas']['SubscriptionWrite'];
type Resend = components['schemas']['NoticeResend'];
type Result = components['schemas']['DecisionRequestRead'];
type History = components['schemas']['NoticeHistory'];
type Intent =
	| { operation: 'subscription'; body: Write }
	| { operation: 'resend'; body: Resend; noticeId: string };
function validationRefusal(error: unknown, status: number | undefined): string | null {
	if (status !== 422 || !error || typeof error !== 'object' || !('detail' in error)) return null;
	const details = error.detail;
	if (!Array.isArray(details) || details.length === 0) return null;
	if (
		!details.every(
			(item) =>
				item &&
				typeof item === 'object' &&
				Array.isArray(item.loc) &&
				['body', 'query', 'path'].includes(item.loc[0]) &&
				typeof item.type === 'string' &&
				typeof item.msg === 'string'
		)
	)
		return null;
	return details.map((item) => `${item.loc.join('.')}: ${item.msg}`).join('; ');
}

export class DecisionNoticeState {
	current = $state<Read | null>(null);
	history = $state<History | null>(null);
	intent = $state<Intent | null>(null);
	outcome = $state<Result | null>(null);
	status = $state<'unknown' | 'recorded' | 'refused' | ''>('');
	busy = $state(false);
	error = $state('');
	constructor(readonly channelId: string) {}
	get unresolved() {
		return this.intent !== null && this.status === 'unknown';
	}
	async refresh(cursor?: string) {
		const { data } = await api.GET(
			'/api/v1/notification-channels/{channel_id}/decision-subscription',
			{ params: { path: { channel_id: this.channelId } } }
		);
		if (!data?.settings || typeof data.revision !== 'number')
			throw new Error('Could not refresh decision subscription');
		this.current = data;
		const result = await api.GET('/api/v1/notification-channels/{channel_id}/decision-notices', {
			params: { path: { channel_id: this.channelId }, query: { cursor, limit: 20 } }
		});
		if (!result.data) throw new Error('Could not refresh decision delivery history');
		this.history =
			cursor && this.history
				? { ...result.data, items: [...this.history.items, ...result.data.items] }
				: result.data;
	}
	async load(cursor?: string) {
		this.busy = true;
		this.error = '';
		try {
			await this.refresh(cursor);
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Refresh failed';
		} finally {
			this.busy = false;
		}
	}
	async save(body: Write) {
		if (this.unresolved || this.busy) return;
		this.intent = { operation: 'subscription', body: JSON.parse(JSON.stringify(body)) };
		await this.retry();
	}
	async resend(noticeId: string, body: Resend) {
		if (this.unresolved || this.busy) return;
		this.intent = { operation: 'resend', noticeId, body: JSON.parse(JSON.stringify(body)) };
		await this.retry();
	}
	async retry() {
		const intent = this.intent;
		if (!intent || this.busy) return;
		this.status = 'unknown';
		this.busy = true;
		this.error = '';
		try {
			const result =
				intent.operation === 'subscription'
					? await api.PUT('/api/v1/notification-channels/{channel_id}/decision-subscription', {
							params: { path: { channel_id: this.channelId } },
							body: intent.body
						})
					: await api.POST(
							'/api/v1/notification-channels/{channel_id}/decision-notices/{notice_id}/resend',
							{
								params: { path: { channel_id: this.channelId, notice_id: intent.noticeId } },
								body: intent.body
							}
						);
			if (!result.data) {
				const invalid = validationRefusal(result.error, result.response?.status);
				if ((result.error as { code?: string })?.code === 'DECISION_NOTICE_REFUSED' || invalid)
					this.status = 'refused';
				if (invalid) throw new Error('Request refused before admission: ' + invalid);
				throw new Error(
					this.status === 'refused'
						? 'Request refused. Refresh and review corrected input.'
						: 'Outcome unknown. Check the original request before another change.'
				);
			}
			this.outcome = result.data;
			this.status = 'recorded';
			try {
				await this.refresh();
			} catch {
				this.error = 'Request recorded; refresh failed. Keep the recorded receipt.';
			}
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Outcome unknown';
		} finally {
			this.busy = false;
		}
	}
	async check() {
		if (!this.intent || this.busy) return;
		this.busy = true;
		this.error = '';
		try {
			const result = await api.GET(
				'/api/v1/notification-channels/{channel_id}/decision-requests/{request_id}',
				{
					params: {
						path: { channel_id: this.channelId, request_id: this.intent.body.request_id },
						query: { operation: this.intent.operation }
					}
				}
			);
			if (!result.data) throw new Error('Outcome unavailable; original intent retained');
			this.outcome = result.data;
			if (result.data.record_state === 'recorded') this.status = 'recorded';
		} catch (e) {
			this.error = e instanceof Error ? e.message : 'Outcome unknown';
		} finally {
			this.busy = false;
		}
	}
	dismiss() {
		if (!this.unresolved) {
			this.intent = null;
			this.outcome = null;
			this.status = '';
		}
	}
}
const states = new SvelteMap<string, DecisionNoticeState>();
let accountGeneration = session.generation;
export function decisionNoticeState(id: string) {
	if (accountGeneration !== session.generation) {
		states.clear();
		accountGeneration = session.generation;
	}
	let value = states.get(id);
	if (!value) {
		value = new DecisionNoticeState(id);
		states.set(id, value);
	}
	return value;
}
