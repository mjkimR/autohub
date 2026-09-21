<script lang="ts">
	import LoadError from '$lib/components/shared/LoadError.svelte';
	import { onMount } from 'svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import {
		Dialog,
		DialogContent,
		DialogDescription,
		DialogFooter,
		DialogHeader,
		DialogTitle
	} from '$lib/components/ui/dialog';
	import { Input } from '$lib/components/ui/input';
	import { BellRing, Plus, RefreshCw, Send } from '@lucide/svelte';
	import {
		NotificationChannelsState,
		type ChannelForm,
		type NotificationChannel
	} from './notifications.svelte';

	const channels = new NotificationChannelsState();
	let dialogOpen = $state(false);
	let editing = $state<NotificationChannel | null>(null);
	let form = $state<ChannelForm>({ name: '', chatId: '', botToken: '', minLevel: 'info' });

	function openCreate() {
		editing = null;
		form = { name: '', chatId: '', botToken: '', minLevel: 'info' };
		dialogOpen = true;
	}

	function openEdit(channel: NotificationChannel) {
		editing = channel;
		form = {
			name: channel.name,
			chatId: channel.chat_id ?? '',
			botToken: '',
			minLevel: channel.min_level
		};
		dialogOpen = true;
	}

	async function save(event: SubmitEvent) {
		event.preventDefault();
		const saved = editing ? await channels.update(editing.id, form) : await channels.create(form);
		if (saved) dialogOpen = false;
	}

	async function remove(channel: NotificationChannel) {
		if (confirm(`Delete notification channel "${channel.name}"?`))
			await channels.remove(channel.id);
	}

	onMount(() => channels.load());
</script>

<div class="space-y-6">
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-3xl font-bold tracking-tight">Notifications</h1>
			<p class="text-sm text-muted-foreground">
				Where the hub reaches you when a run pauses, is blocked, or fails, when an @auto-run could
				not be handled, and when the scheduler trigger stops firing. Every enabled channel receives
				every notice.
			</p>
		</div>
		<div class="flex gap-2">
			<Button
				variant="outline"
				size="sm"
				onclick={() => channels.load()}
				disabled={channels.loading}
				class="gap-2"
			>
				<RefreshCw class="size-4 {channels.loading ? 'animate-spin' : ''}" /> Refresh
			</Button>
			<Button size="sm" onclick={openCreate} class="gap-2">
				<Plus class="size-4" /> Add Telegram channel
			</Button>
		</div>
	</div>

	{#if channels.error}
		<LoadError message={channels.error} retry={() => channels.load()} />
	{:else if channels.loading && channels.items.length === 0}
		<div class="flex h-40 items-center justify-center text-sm text-muted-foreground">
			Loading notification channels…
		</div>
	{:else if channels.items.length === 0}
		<Card class="border-border/80 bg-card/60">
			<CardContent class="space-y-2 p-6 text-sm text-muted-foreground">
				<p class="font-medium text-foreground">No channel yet: the hub stops silently.</p>
				<ol class="list-decimal space-y-1 pl-5">
					<li>In Telegram, message @BotFather, send /newbot, and copy the bot token.</li>
					<li>Send any message to your new bot so it may write to you.</li>
					<li>
						Open https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates and copy <code>chat.id</code>.
					</li>
					<li>Add the channel here and send a test.</li>
				</ol>
			</CardContent>
		</Card>
	{:else}
		<div class="grid gap-5 lg:grid-cols-2">
			{#each channels.items as channel (channel.id)}
				<Card class="border-border/80 bg-card/60">
					<CardHeader class="pb-3">
						<div class="flex items-start justify-between gap-4">
							<div class="flex gap-3">
								<div
									class="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary"
								>
									<BellRing class="size-5" />
								</div>
								<div>
									<CardTitle class="text-base">{channel.name}</CardTitle>
									<p class="mt-1 text-xs text-muted-foreground">
										{channel.kind} · chat {channel.chat_id ?? 'not set'}
									</p>
								</div>
							</div>
							<div class="flex items-center gap-1.5">
								<Badge variant="outline" class="font-mono text-[10px] uppercase">
									{channel.min_level}
								</Badge>
								<Badge variant={channel.enabled ? 'default' : 'secondary'}
									>{channel.enabled ? 'enabled' : 'disabled'}</Badge
								>
							</div>
						</div>
					</CardHeader>
					<CardContent class="space-y-3 text-sm">
						<p class="text-xs text-muted-foreground">
							{channel.last_sent_at
								? `Last delivered ${new Date(channel.last_sent_at).toLocaleString()}`
								: 'Nothing delivered yet'}
						</p>
						{#if channel.last_error}
							<p class="text-xs text-destructive">Last delivery failed: {channel.last_error}</p>
						{/if}
						<div class="flex flex-wrap gap-2">
							<Button
								variant="outline"
								size="sm"
								class="gap-2"
								disabled={channels.testingId === channel.id}
								onclick={() => channels.sendTest(channel.id)}
							>
								<Send class="size-4" /> Send test
							</Button>
							<Button variant="outline" size="sm" onclick={() => openEdit(channel)}>Edit</Button>
							<Button
								variant="outline"
								size="sm"
								onclick={() => channels.setEnabled(channel.id, !channel.enabled)}
								>{channel.enabled ? 'Disable' : 'Enable'}</Button
							>
							<Button variant="outline" size="sm" onclick={() => remove(channel)}>Delete</Button>
						</div>
					</CardContent>
				</Card>
			{/each}
		</div>
	{/if}
</div>

<Dialog bind:open={dialogOpen}>
	<DialogContent class="sm:max-w-md">
		<DialogHeader>
			<DialogTitle>{editing ? 'Edit Telegram channel' : 'Add Telegram channel'}</DialogTitle>
			<DialogDescription>
				The bot token is encrypted at rest and never shown again.
			</DialogDescription>
		</DialogHeader>
		<form onsubmit={save} class="space-y-4">
			<label class="grid gap-1 text-sm font-medium">
				Name
				<Input bind:value={form.name} required placeholder="My phone" />
			</label>
			<label class="grid gap-1 text-sm font-medium">
				Chat ID
				<Input bind:value={form.chatId} required placeholder="123456789" />
			</label>
			<label class="grid gap-1 text-sm font-medium">
				Minimum notification level
				<select
					bind:value={form.minLevel}
					class="h-9 rounded-md border border-input bg-transparent px-3 text-sm text-foreground"
				>
					<option value="debug" class="bg-background text-foreground"
						>DEBUG — all trace and raw events</option
					>
					<option value="info" class="bg-background text-foreground"
						>INFO — routine progress and normal triggers</option
					>
					<option value="warning" class="bg-background text-foreground"
						>WARNING — delays, waiting runs, lockouts</option
					>
					<option value="error" class="bg-background text-foreground"
						>ERROR — paused/blocked runs, failed replay</option
					>
					<option value="critical" class="bg-background text-foreground"
						>CRITICAL — service stoppage, fatal errors</option
					>
				</select>
			</label>
			<label class="grid gap-1 text-sm font-medium">
				Bot token
				<Input
					type="password"
					bind:value={form.botToken}
					required={!editing}
					autocomplete="off"
					placeholder={editing ? 'Leave empty to keep the stored token' : '123456:ABC…'}
				/>
			</label>
			<DialogFooter>
				<Button type="button" variant="outline" onclick={() => (dialogOpen = false)}>Cancel</Button>
				<Button type="submit" disabled={channels.saving}>Save</Button>
			</DialogFooter>
		</form>
	</DialogContent>
</Dialog>
