<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import {
		Table,
		TableBody,
		TableCell,
		TableHead,
		TableHeader,
		TableRow
	} from '$lib/components/ui/table';
	import { RefreshCw } from '@lucide/svelte';
	import { toast } from 'svelte-sonner';

	type Delivery = components['schemas']['GitHubWebhookDeliveryRead'];
	type Status = 'received' | 'retrying' | 'processed' | 'failed';

	const PAGE_SIZE = 50;

	let loading = $state(true);
	let items = $state<Delivery[]>([]);
	let total = $state(0);
	let offset = $state(0);
	// Most deliveries are routine pushes and CI events; the default shows what an operator would look for.
	let noteworthy = $state(true);
	let status = $state<Status | ''>('');

	const firstShown = $derived(items.length === 0 ? 0 : offset + 1);
	const lastShown = $derived(offset + items.length);

	async function load(pageOffset: number) {
		loading = true;
		try {
			const res = await api.GET('/api/v1/github-webhook-deliveries', {
				params: {
					query: {
						offset: pageOffset,
						limit: PAGE_SIZE,
						noteworthy,
						...(status ? { status } : {})
					}
				}
			});
			if (res.error) {
				toast.error('Failed to load webhook deliveries');
				return;
			}
			items = res.data?.items ?? [];
			total = res.data?.total_count ?? 0;
			offset = pageOffset;
		} catch {
			toast.error('Failed to load webhook deliveries');
		} finally {
			loading = false;
		}
	}

	function outcome(delivery: Delivery) {
		if (delivery.failure_detail) return delivery.failure_detail;
		if (delivery.status === 'received')
			return 'Waiting to be processed; replayed by the next tick if lost';
		if (delivery.status === 'retrying') return 'Being replayed';
		return delivery.auto_run ? 'Enrolled or advanced the pull request' : '';
	}

	onMount(() => load(0));
</script>

<div class="space-y-6">
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-3xl font-bold tracking-tight">Webhook deliveries</h1>
			<p class="text-sm text-muted-foreground">
				What GitHub sent and what came of it, including why an @auto-run did not enroll or dispatch.
				Payloads are not kept. Deliveries are deleted after 90 days.
			</p>
		</div>
		<Button
			variant="outline"
			size="sm"
			onclick={() => load(offset)}
			disabled={loading}
			class="gap-2"
		>
			<RefreshCw class="size-4 {loading ? 'animate-spin' : ''}" /> Refresh
		</Button>
	</div>

	<div class="flex flex-wrap items-center gap-4 text-sm">
		<label class="flex items-center gap-2 font-medium">
			<input type="checkbox" bind:checked={noteworthy} onchange={() => load(0)} />
			Only triggers and problems
		</label>
		<label class="flex items-center gap-2 font-medium">
			Status
			<select
				bind:value={status}
				onchange={() => load(0)}
				class="h-9 rounded-md border border-input bg-transparent px-3 text-sm"
			>
				<option value="">Any</option>
				<option value="received">Received</option>
				<option value="retrying">Retrying</option>
				<option value="processed">Processed</option>
				<option value="failed">Failed</option>
			</select>
		</label>
	</div>

	<div class="rounded-xl border border-border/80 bg-card/60">
		<Table>
			<TableHeader>
				<TableRow>
					<TableHead class="w-[170px]">Received</TableHead>
					<TableHead class="w-[150px]">Event</TableHead>
					<TableHead>Pull request</TableHead>
					<TableHead class="w-[110px]">Status</TableHead>
					<TableHead>Outcome</TableHead>
				</TableRow>
			</TableHeader>
			<TableBody>
				{#if loading && items.length === 0}
					<TableRow>
						<TableCell colspan={5} class="h-24 text-center text-muted-foreground"
							>Loading webhook deliveries…</TableCell
						>
					</TableRow>
				{:else if items.length === 0}
					<TableRow>
						<TableCell colspan={5} class="h-24 text-center text-muted-foreground">
							{noteworthy || status ? 'No deliveries match.' : 'No deliveries received yet.'}
						</TableCell>
					</TableRow>
				{:else}
					{#each items as delivery (delivery.id)}
						<TableRow>
							<TableCell class="text-xs">{new Date(delivery.created_at).toLocaleString()}</TableCell
							>
							<TableCell class="font-mono text-xs">
								{delivery.event}
								{#if delivery.auto_run}
									<Badge variant="outline" class="ml-1"
										>@auto-run{delivery.requested_catalog
											? `:${delivery.requested_catalog}`
											: ''}</Badge
									>
								{/if}
							</TableCell>
							<TableCell class="text-xs">
								{delivery.repository ?? '—'}{delivery.pull_number ? `#${delivery.pull_number}` : ''}
							</TableCell>
							<TableCell>
								<Badge
									variant={delivery.status === 'failed'
										? 'destructive'
										: delivery.status === 'processed'
											? 'secondary'
											: 'outline'}>{delivery.status}</Badge
								>
								{#if delivery.attempts > 1}
									<span class="ml-1 text-[10px] text-muted-foreground">×{delivery.attempts}</span>
								{/if}
							</TableCell>
							<TableCell class="text-xs whitespace-normal text-muted-foreground"
								>{outcome(delivery)}</TableCell
							>
						</TableRow>
					{/each}
				{/if}
			</TableBody>
		</Table>
	</div>

	<div class="flex items-center justify-between">
		<span class="text-xs text-muted-foreground">{firstShown}–{lastShown} of {total}</span>
		<div class="flex gap-2">
			<Button
				variant="outline"
				size="sm"
				disabled={loading || offset === 0}
				onclick={() => load(Math.max(0, offset - PAGE_SIZE))}>Previous</Button
			>
			<Button
				variant="outline"
				size="sm"
				disabled={loading || offset + PAGE_SIZE >= total}
				onclick={() => load(offset + PAGE_SIZE)}>Next</Button
			>
		</div>
	</div>
</div>
