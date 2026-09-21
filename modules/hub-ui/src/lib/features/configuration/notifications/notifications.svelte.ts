import { api, type components } from '$lib/api';
import { apiErrorMessage } from '$lib/api/errors';
import { responseData } from '$lib/api/pagination';
import { toast } from 'svelte-sonner';

export type NotificationChannel = components['schemas']['NotificationChannelRead'];

export type ChannelForm = { name: string; chatId: string; botToken: string };

export class NotificationChannelsState {
	items = $state<NotificationChannel[]>([]);
	loading = $state(false);
	error = $state('');
	saving = $state(false);
	testingId = $state<string | null>(null);

	async load() {
		this.loading = true;
		this.error = '';
		try {
			const res = await api.GET('/api/v1/notification-channels');
			this.items = responseData(res, 'Failed to load notification channels').items;
		} catch {
			this.error = 'Failed to load notification channels';
			toast.error(this.error);
		} finally {
			this.loading = false;
		}
	}

	async create(form: ChannelForm) {
		this.saving = true;
		try {
			const res = await api.POST('/api/v1/notification-channels', {
				body: {
					name: form.name.trim(),
					kind: 'telegram',
					enabled: true,
					chat_id: form.chatId.trim(),
					bot_token: form.botToken.trim()
				}
			});
			if (res.error) {
				toast.error(apiErrorMessage(res.error, 'Failed to add the notification channel'));
				return false;
			}
			toast.success('Notification channel added. Send a test to confirm it reaches you.');
			await this.load();
			return true;
		} catch {
			toast.error('Request failed. Check your connection and retry.');
			return false;
		} finally {
			this.saving = false;
		}
	}

	/** An empty bot token keeps the stored one. */
	async update(id: string, form: ChannelForm) {
		this.saving = true;
		try {
			const res = await api.PATCH('/api/v1/notification-channels/{channel_id}', {
				params: { path: { channel_id: id } },
				body: {
					name: form.name.trim(),
					chat_id: form.chatId.trim(),
					...(form.botToken.trim() ? { bot_token: form.botToken.trim() } : {})
				}
			});
			if (res.error) {
				toast.error(apiErrorMessage(res.error, 'Failed to update the notification channel'));
				return false;
			}
			toast.success('Notification channel updated');
			await this.load();
			return true;
		} catch {
			toast.error('Request failed. Check your connection and retry.');
			return false;
		} finally {
			this.saving = false;
		}
	}

	async setEnabled(id: string, enabled: boolean) {
		try {
			const res = await api.PATCH('/api/v1/notification-channels/{channel_id}', {
				params: { path: { channel_id: id } },
				body: { enabled }
			});
			if (res.error) {
				toast.error(apiErrorMessage(res.error, 'Failed to update the notification channel'));
				return;
			}
			await this.load();
		} catch {
			toast.error('Request failed. Check your connection and retry.');
		}
	}

	async remove(id: string) {
		try {
			const res = await api.DELETE('/api/v1/notification-channels/{channel_id}', {
				params: { path: { channel_id: id } }
			});
			if (res.error) {
				toast.error(apiErrorMessage(res.error, 'Failed to delete the notification channel'));
				return;
			} else toast.success('Notification channel deleted');
			await this.load();
		} catch {
			toast.error('Request failed. Check your connection and retry.');
		}
	}

	async sendTest(id: string) {
		this.testingId = id;
		try {
			const res = await api.POST('/api/v1/notification-channels/{channel_id}/test', {
				params: { path: { channel_id: id } }
			});
			if (res.error)
				toast.error(apiErrorMessage(res.error, 'Failed to send the test notification'));
			else if (res.data?.delivered) toast.success('Test notification delivered');
			else toast.error(res.data?.detail ?? 'The test notification was not delivered');
			await this.load();
		} catch {
			toast.error('Request failed. Check your connection and retry.');
			return false;
		} finally {
			this.testingId = null;
		}
	}
}
