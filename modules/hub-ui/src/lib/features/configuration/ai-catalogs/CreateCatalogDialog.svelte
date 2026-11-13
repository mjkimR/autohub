<script lang="ts">
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { Button } from '$lib/components/ui/button';
	import {
		Dialog,
		DialogContent,
		DialogDescription,
		DialogFooter,
		DialogHeader,
		DialogTitle
	} from '$lib/components/ui/dialog';
	import { Input } from '$lib/components/ui/input';
	import type { AICatalogsState, CreateAICatalog } from './ai-catalogs.svelte';

	let { catalogs, onclose }: { catalogs: AICatalogsState; onclose: () => void } = $props();
	let open = $state(true);
	let name = $state('');
	let key = $state('');
	let kind = $state<CreateAICatalog['kind']>('codex');
	let connectorId = $state('');
	let concurrency = $state<number | undefined>(1);
	let dailyLimit = $state<number | undefined>(100);
	const connectors = $derived(
		catalogs.connectors.filter((item) => item.provider === 'jules' && item.enabled)
	);

	$effect(() => {
		if (!open) onclose();
	});

	async function save(event: SubmitEvent) {
		event.preventDefault();
		if (!name.trim() || !/^[a-z][a-z0-9_-]{0,99}$/.test(key.trim())) return;
		if (!concurrency || !Number.isInteger(concurrency) || concurrency < 1 || concurrency > 1000)
			return;
		if (
			kind === 'jules' &&
			(!dailyLimit || !Number.isInteger(dailyLimit) || dailyLimit < 1 || dailyLimit > 10000)
		)
			return;
		if (
			await catalogs.create({
				name: name.trim(),
				key: key.trim(),
				kind,
				connector_id: kind === 'jules' ? connectorId || null : null,
				configured_concurrency: concurrency,
				policy_config:
					kind === 'jules'
						? { daily_task_limit: dailyLimit, window: 'rolling', timezone: 'UTC' }
						: {},
				enabled: true
			})
		)
			open = false;
	}
</script>

<Dialog bind:open>
	<!-- eslint-disable-next-line shadcn/no-arbitrary-values -- viewport-relative height has no scale equivalent -->
	<DialogContent class="max-h-[90dvh] overflow-y-auto">
		<DialogHeader>
			<DialogTitle>Add AI catalog</DialogTitle>
			<DialogDescription>
				Create a catalog with its own usage limits, then select it in a project or agent schedule.
			</DialogDescription>
		</DialogHeader>
		<form onsubmit={save}>
			<fieldset disabled={catalogs.saving} class="space-y-4">
				<label class="grid gap-1 text-sm font-medium">
					Name
					<Input bind:value={name} maxlength={255} placeholder="Team Jules" required />
				</label>
				<label class="grid gap-1 text-sm font-medium">
					Catalog key
					<Input
						bind:value={key}
						maxlength={100}
						pattern="[a-z][a-z0-9_\-]*"
						placeholder="team-jules"
						required
					/>
					<span class="text-xs font-normal text-muted-foreground"
						>Unique, permanent identifier for this catalog. Start with a lowercase letter; use
						lowercase letters, digits, hyphens or underscores.</span
					>
				</label>
				<label class="grid gap-1 text-sm font-medium">
					Provider
					<NativeSelect bind:value={kind}>
						<option value="codex">Codex</option>
						<option value="jules">Jules</option>
					</NativeSelect>
				</label>
				{#if kind === 'jules'}
					<label class="grid gap-1 text-sm font-medium">
						Jules connector
						<NativeSelect bind:value={connectorId}>
							<option value="">Connect later</option>
							{#each connectors as connector (connector.id)}
								<option value={connector.id}>{connector.name}</option>
							{/each}
						</NativeSelect>
					</label>
					<p class="text-xs text-muted-foreground">
						Register API keys in Connectors. Sessions require an enabled Jules connector.
					</p>
					<label class="grid gap-1 text-sm font-medium">
						Daily task limit
						<Input type="number" min="1" max="10000" step="1" bind:value={dailyLimit} required />
					</label>
					<p class="text-xs text-muted-foreground">
						Counted over a rolling 24 hours. Set this to your account's allowance.
					</p>
				{:else}
					<p class="text-xs text-muted-foreground">
						Codex uses the selected project's GitHub connection and Codex setup. A new catalog does
						not sign in to a different Codex account.
					</p>
				{/if}
				<label class="grid gap-1 text-sm font-medium">
					Concurrent work limit
					<Input type="number" min="1" max="1000" step="1" bind:value={concurrency} required />
				</label>
				<p class="text-xs text-muted-foreground">
					Catalogs track usage separately. Use one catalog per account to keep its limit accurate.
				</p>
				<DialogFooter>
					<Button type="button" variant="outline" onclick={() => (open = false)}>Cancel</Button>
					<Button type="submit">Create catalog</Button>
				</DialogFooter>
			</fieldset>
		</form>
	</DialogContent>
</Dialog>
