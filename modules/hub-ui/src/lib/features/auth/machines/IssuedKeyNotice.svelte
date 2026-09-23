<script lang="ts">
	import type { components } from '$lib/api/schema';
	import { Button } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';

	type Issued = components['schemas']['KeyIssued'];
	let { issued, mcp, ondismiss }: { issued: Issued; mcp: boolean; ondismiss: () => void } =
		$props();

	const endpoint = `${window.location.origin}/mcp/`;
	const claudeCommand = $derived(
		`claude mcp add --transport http autohub ${endpoint} --header "Authorization: Bearer ${issued.key}"`
	);
	const codexConfig = `[mcp_servers.autohub]\nurl = "${endpoint}"\nbearer_token_env_var = "AUTOHUB_MCP_KEY"`;

	async function copy(text: string, what: string) {
		try {
			await navigator.clipboard.writeText(text);
			toast.success(`${what} copied`);
		} catch {
			toast.error('Could not copy. Select the text and copy it manually.');
		}
	}
</script>

<section class="space-y-3 rounded-lg border border-primary p-4" aria-label="Issued key">
	<h3 class="font-semibold">Key issued: {issued.label}</h3>
	<p class="text-sm text-muted-foreground">
		This key is shown only once. Store it now; it cannot be retrieved later.
	</p>
	<div class="flex items-center gap-2">
		<code class="min-w-0 flex-1 rounded bg-muted p-2 text-xs break-all" data-testid="issued-key"
			>{issued.key}</code
		>
		<Button size="sm" variant="outline" onclick={() => copy(issued.key, 'Key')}>Copy key</Button>
	</div>
	{#if mcp}
		<div class="space-y-2">
			<p class="text-sm font-medium">Claude Code (run in the project directory)</p>
			<div class="flex items-start gap-2">
				<code class="min-w-0 flex-1 rounded bg-muted p-2 text-xs break-all">{claudeCommand}</code>
				<Button size="sm" variant="outline" onclick={() => copy(claudeCommand, 'Command')}
					>Copy</Button
				>
			</div>
			<p class="text-sm font-medium">Codex (~/.codex/config.toml, key in AUTOHUB_MCP_KEY)</p>
			<div class="flex items-start gap-2">
				<pre class="min-w-0 flex-1 overflow-x-auto rounded bg-muted p-2 text-xs">{codexConfig}</pre>
				<Button size="sm" variant="outline" onclick={() => copy(codexConfig, 'Config')}>Copy</Button
				>
			</div>
		</div>
	{/if}
	<Button size="sm" onclick={ondismiss}>I stored the key</Button>
</section>
