<script lang="ts">
	import { untrack } from 'svelte';
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
	import type { CatalogDialogProps } from './catalog-kinds';

	let { catalog, catalogs, onclose }: CatalogDialogProps = $props();

	let open = $state(true);
	let concurrency = $state<number | undefined>(untrack(() => catalog.configured_concurrency));

	$effect(() => {
		if (!open) onclose();
	});

	async function save(event: SubmitEvent) {
		event.preventDefault();
		if (!concurrency || !Number.isInteger(concurrency) || concurrency < 1 || concurrency > 1000)
			return;
		if (await catalogs.setConcurrency(catalog.key, concurrency)) open = false;
	}
</script>

<Dialog bind:open>
	<DialogContent>
		<DialogHeader>
			<DialogTitle>Catalog concurrency</DialogTitle>
			<DialogDescription>
				All projects and schedules on {catalog.name} share this limit. Match it to the account; lowering
				it lets work already running finish.
			</DialogDescription>
		</DialogHeader>
		<form onsubmit={save} class="space-y-4">
			<label class="grid gap-1 text-sm font-medium">
				Concurrent work limit
				<Input type="number" min="1" max="1000" step="1" bind:value={concurrency} required />
			</label>
			<DialogFooter>
				<Button type="button" variant="outline" onclick={() => (open = false)}>Cancel</Button>
				<Button type="submit" disabled={catalogs.saving}>Save limit</Button>
			</DialogFooter>
		</form>
	</DialogContent>
</Dialog>
