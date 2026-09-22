<script lang="ts">
	import { untrack } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogDescription,
		DialogFooter
	} from '$lib/components/ui/dialog';
	import type { CatalogDialogProps } from './catalog-kinds';

	let { catalog, catalogs, onclose }: CatalogDialogProps = $props();
	const initial = untrack(() => catalog);
	const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
	function localInput(value: string | null) {
		if (!value) return '';
		const date = new Date(value);
		if (Number.isNaN(date.getTime())) return '';
		const pad = (n: number) => String(n).padStart(2, '0');
		return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
	}
	let availableAt = $state(localInput(initial.available_at));
	let note = $state(initial.availability_note ?? '');
	const preview = $derived(
		availableAt && !Number.isNaN(new Date(availableAt).getTime())
			? new Date(availableAt).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
			: ''
	);
	async function save(event: SubmitEvent) {
		event.preventDefault();
		if (catalogs.saving) return;
		if (await catalogs.setAvailability(catalog.key, availableAt, note)) onclose();
	}
</script>

<Dialog
	open={true}
	onOpenChange={(open) => {
		if (!open) onclose();
	}}
>
	<DialogContent class="max-h-[calc(100dvh-2rem)] min-w-0 overflow-y-auto [overflow-wrap:anywhere]">
		<DialogHeader>
			<DialogTitle>Set catalog refresh time</DialogTitle>
			<DialogDescription
				>This global hold affects all work assigned to this catalog.</DialogDescription
			>
		</DialogHeader>
		<div class="rounded-lg bg-muted/50 p-3 text-sm">
			<p class="font-semibold">{catalog.name}</p>
			<p class="text-xs text-muted-foreground">{catalog.key}</p>
			<p class="mt-2">
				Current: {catalog.available_at
					? new Date(catalog.available_at).toLocaleString()
					: 'Available now'}
			</p>
			<p class="mt-1 text-muted-foreground">Timezone: {timezone}</p>
		</div>
		<form onsubmit={save} class="min-w-0 space-y-4">
			<div class="space-y-2">
				<label for="catalog-refresh-time" class="text-sm font-medium">Refresh time</label>
				<Input
					id="catalog-refresh-time"
					type="datetime-local"
					class="h-11 max-w-full min-w-0 text-base"
					bind:value={availableAt}
					required
					aria-describedby="refresh-time-preview"
				/>
				<p id="refresh-time-preview" class="text-sm text-muted-foreground" aria-live="polite">
					{preview
						? `Will resume: ${preview} (${timezone})`
						: `Enter a future date and time in ${timezone}.`}
				</p>
			</div>
			<div class="space-y-2">
				<label for="catalog-refresh-note" class="text-sm font-medium"
					>Operator note (optional)</label
				>
				<Input
					id="catalog-refresh-note"
					class="h-11 text-base"
					bind:value={note}
					maxlength={500}
					placeholder="Optional operator note"
				/>
			</div>
			<DialogFooter class="gap-2 [&_button]:min-h-11">
				<Button type="button" variant="outline" onclick={onclose}>Cancel</Button>
				<Button type="submit" disabled={catalogs.saving}
					>{catalogs.saving ? 'Saving…' : 'Save global hold'}</Button
				>
			</DialogFooter>
		</form>
	</DialogContent>
</Dialog>
