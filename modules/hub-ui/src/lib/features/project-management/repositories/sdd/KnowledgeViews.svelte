<script lang="ts">
	import { tick, untrack } from 'svelte';
	import type { RepositoryDataSource } from './repository';
	import {
		indexDocuments,
		taskProgress,
		renderDocument,
		documentAnchor,
		bookGroup,
		bookGroups,
		namespaceOf,
		idIndex,
		type RepositoryDocument
	} from './documents';

	let {
		view,
		source,
		branch,
		theme,
		requestedPath,
		requestedAnchor,
		onOpen,
		onLocation,
		diagrams
	} = $props<{
		view: 'book' | 'proposals' | 'specs';
		theme: string;
		requestedPath: string;
		requestedAnchor: string;
		source: RepositoryDataSource | null;
		branch: string;
		onOpen: (path: string) => void;
		onLocation: (path: string, anchor: string, view: string, meta: Record<string, any>) => void;
		diagrams: (node: HTMLElement) => { destroy: () => void };
	}>();
	let documents = $state<RepositoryDocument[]>([]);
	let errors = $state<string[]>([]);
	let loading = $state(false);
	let query = $state('');
	let status = $state('');
	let priority = $state('');
	let size = $state('');
	let area = $state('');
	let namespace = $state('all');
	let includeCompleted = $state(false);
	let selectedPath = $state('');
	let detailPath = $state('');
	let currentAnchor = $state('');
	let root: HTMLElement;

	$effect(() => {
		const repository = source,
			ref = branch;
		const controller = new AbortController();
		documents = [];
		errors = [];
		loading = Boolean(repository);
		selectedPath = '';
		detailPath = '';
		currentAnchor = '';
		if (repository)
			void indexDocuments(repository, ref, controller.signal).then((result) => {
				if (controller.signal.aborted) return;
				documents = result.documents;
				errors = result.errors;
				loading = false;
			});
		return () => controller.abort();
	});
	$effect(() => {
		view;
		query = '';
		status = '';
		priority = '';
		size = '';
		area = '';
		selectedPath = '';
		detailPath = '';
		currentAnchor = '';
	});
	const namespaces = $derived([...new Set(documents.map(namespaceOf))].sort());
	const scoped = $derived(
		documents.filter(
			(d) => namespace === 'all' || namespaceOf(d) === namespace || namespaceOf(d) === 'global'
		)
	);
	const ids = $derived(idIndex(documents));
	const book = $derived(
		bookGroups.flatMap((group) => scoped.filter((d) => bookGroup(d) === group))
	);
	const candidates = $derived(
		scoped.filter((d) =>
			view === 'proposals'
				? /^docs\/proposals\/PROP-[^/]+\/proposal\.md$/.test(d.path)
				: /^specs\/\d{4}-\d{2}\/[^/]+\/spec\.md$/.test(d.path)
		)
	);
	const statuses = $derived(
		[...new Set(candidates.map((d) => String(d.meta.status ?? 'unknown')))].sort()
	);
	const areas = $derived(
		[...new Set(candidates.map((d) => String(d.meta.target_area ?? '')).filter(Boolean))].sort()
	);
	const entries = $derived(
		candidates.filter(
			(d) =>
				(view !== 'specs' || includeCompleted || d.meta.status !== 'completed') &&
				(!status || String(d.meta.status ?? 'unknown') === status) &&
				(!priority || d.meta.priority === priority) &&
				(!size || d.meta.size === size) &&
				(!area || d.meta.target_area === area) &&
				(!query ||
					`${d.title} ${d.meta.id ?? ''} ${d.meta.target_area ?? ''}`
						.toLowerCase()
						.includes(query.toLowerCase()))
		)
	);
	const selected = $derived(entries.find((d) => d.path === selectedPath));
	const bundle = $derived(
		selected
			? documents
					.filter((d) =>
						d.path.startsWith(selected.path.slice(0, selected.path.lastIndexOf('/') + 1))
					)
					.sort((a, b) => {
						const order = [
							'proposal.md',
							'spec.md',
							'target-docs.md',
							'plan.md',
							'tasks.md',
							'reconcile.md'
						];
						const rank = (d: RepositoryDocument) => {
							const i = order.indexOf(d.path.split('/').at(-1)!);
							return i < 0 ? 99 : i;
						};
						return rank(a) - rank(b) || a.path.localeCompare(b.path);
					})
			: []
	);
	const detail = $derived(bundle.find((d) => d.path === detailPath) ?? selected);
	const visibleDocs = $derived(view === 'book' ? book : detail ? [detail] : []);
	const rendered = $derived(
		new Map(visibleDocs.map((doc) => [doc.path, renderDocument(doc, documents)]))
	);
	const taskDoc = $derived(bundle.find((d) => d.path.endsWith('/tasks.md')));
	const taskChecks = $derived(taskProgress(taskDoc?.body ?? ''));
	const relations = $derived(
		selected
			? ['related_capabilities', 'related_stories'].flatMap((key) =>
					Array.isArray(selected.meta[key]) ? selected.meta[key] : []
				)
			: []
	);

	$effect(() => {
		const path = requestedPath,
			anchor = requestedAnchor,
			currentView = view;
		if (loading || !documents.length) return;
		untrack(() => {
			const doc = documents.find((d) => d.path === path);
			if (!doc) return;
			if (currentView !== 'book') {
				const entry = candidates.find((d) =>
					path.startsWith(d.path.slice(0, d.path.lastIndexOf('/') + 1))
				);
				if (!entry) return;
				if (entry.meta.status === 'completed') includeCompleted = true;
				namespace = 'all';
				status = '';
				query = '';
				priority = '';
				size = '';
				area = '';
				selectedPath = entry.path;
				detailPath = path;
			}
			void tick().then(() => jump(path, anchor || documentAnchor(path)));
		});
	});

	function lazyDiagrams(node: HTMLElement) {
		let cleanup: { destroy: () => void } | undefined;
		const observer = new IntersectionObserver(
			(entries) => {
				if (entries.some((e) => e.isIntersecting)) {
					cleanup = diagrams(node);
					observer.disconnect();
				}
			},
			{ root: root?.querySelector('.reading-content'), rootMargin: '200px' }
		);
		observer.observe(node);
		return {
			destroy() {
				observer.disconnect();
				cleanup?.destroy();
			}
		};
	}
	function trackHeading(node: HTMLElement) {
		const observer = new IntersectionObserver(
			(entries) => {
				const visible = entries.filter((e) => e.isIntersecting);
				if (visible.length) currentAnchor = visible[0].target.id;
			},
			{ root: root?.querySelector('.reading-content'), rootMargin: '0px 0px -70% 0px' }
		);
		node.querySelectorAll('[id]').forEach((heading) => observer.observe(heading));
		return {
			destroy() {
				observer.disconnect();
			}
		};
	}
	async function jump(path: string, anchor = documentAnchor(path)) {
		if (!visibleDocs.some((d) => d.path === path)) {
			const target = documents.find((d) => d.path === path);
			if (!target) return;
			if (view === 'book' && bookGroup(target)) namespace = 'all';
			else if (
				selected &&
				path.startsWith(selected.path.slice(0, selected.path.lastIndexOf('/') + 1))
			)
				detailPath = path;
			else {
				onOpen(path);
				return;
			}
			await tick();
		}
		const element = root.querySelectorAll<HTMLElement>('[id]');
		const destination = [...element].find((el) => el.id === anchor);
		if (!destination) return;
		destination.scrollIntoView({ block: 'start', behavior: 'instant' });
		currentAnchor = anchor;
		onLocation(path, anchor, view, documents.find((d) => d.path === path)?.meta ?? {});
	}
	function linkNavigation(node: HTMLElement) {
		node.addEventListener('click', followLink);
		return {
			destroy() {
				node.removeEventListener('click', followLink);
			}
		};
	}
	function followLink(event: MouseEvent) {
		const link = (event.target as Element).closest<HTMLAnchorElement>('a[data-doc-path]');
		if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
		event.preventDefault();
		void jump(link.dataset.docPath!, link.getAttribute('href')!.slice(1));
	}
	function select(doc: RepositoryDocument) {
		selectedPath = doc.path;
		detailPath = '';
		currentAnchor = '';
		onLocation(doc.path, '', view, doc.meta);
	}
	const fileLabel = (path: string) =>
		({
			'proposal.md': '제안서',
			'spec.md': '요구사항',
			'plan.md': '설계',
			'tasks.md': '태스크',
			'reconcile.md': '문서 반영',
			'target-docs.md': '목표 문서'
		})[path.split('/').at(-1)!] ?? path.split('/').slice(-2).join('/');
</script>

<div class="knowledge" bind:this={root}>
	<div class="filters">
		<label
			>문서 범위 <select aria-label="문서 범위" bind:value={namespace}
				><option value="all">전체</option>{#each namespaces as name}<option value={name}
						>{name === 'global' ? '공통' : name + ' + 공통'}</option
					>{/each}</select
			></label
		>
		{#if view !== 'book'}
			<input aria-label="제목 또는 ID 검색" placeholder="제목 또는 ID 검색" bind:value={query} />
			<select aria-label="상태" bind:value={status}
				><option value="">모든 상태</option>{#each statuses as s}<option value={s}>{s}</option
					>{/each}</select
			>
			{#if view === 'proposals'}
				<select aria-label="우선순위" bind:value={priority}
					><option value="">모든 우선순위</option
					>{#each ['critical', 'high', 'medium', 'low'] as p}<option value={p}>{p}</option
						>{/each}</select
				>
				<select aria-label="규모" bind:value={size}
					><option value="">모든 규모</option>{#each ['S', 'M', 'L', 'XL'] as s}<option value={s}
							>{s}</option
						>{/each}</select
				>
				<select aria-label="대상 영역" bind:value={area}
					><option value="">모든 영역</option>{#each areas as a}<option value={a}>{a}</option
						>{/each}</select
				>
			{:else}
				<label><input type="checkbox" bind:checked={includeCompleted} /> 완료 포함</label>
			{/if}
		{/if}
	</div>
	{#if errors.length}<details class="index-errors">
			<summary>불러오지 못한 문서 {errors.length}개</summary>{#each errors as error}<p>
					{error}
				</p>{/each}
		</details>{/if}
	{#if loading}<p role="status">문서를 불러오는 중…</p>
	{:else if !source}<p>저장소를 연결하면 문서를 탐색할 수 있습니다.</p>
	{:else}
		<div class="reading-layout">
			<aside class="outline" aria-label={view === 'book' ? '전체 목차' : '번들 목록'}>
				{#if view === 'book'}
					{#each bookGroups as group}
						{#if book.some((d) => bookGroup(d) === group)}<h2>{group}</h2>{/if}
						{#each book.filter((d) => bookGroup(d) === group) as doc}
							<button
								class:active={currentAnchor === documentAnchor(doc.path) ||
									currentAnchor === rendered.get(doc.path)?.headings[0]?.id}
								onclick={() => jump(doc.path)}>{doc.title}</button
							>
							{#each rendered
								.get(doc.path)
								?.headings.filter((h) => h.level > 1 && h.level <= 3) ?? [] as heading}
								<button
									class="subheading"
									class:active={currentAnchor === heading.id}
									style:padding-left={`${heading.level * 8}px`}
									onclick={() => jump(doc.path, heading.id)}>{heading.title}</button
								>
							{/each}
						{/each}
					{/each}
				{:else}
					<p class="count">{entries.length}개 {view === 'proposals' ? '제안' : '작업 명세'}</p>
					{#each entries as doc}
						<button
							class="entry"
							class:active={selected?.path === doc.path}
							onclick={() => select(doc)}
						>
							<strong>{doc.title}</strong><span>{doc.meta.id}</span>
							<span
								>{[
									doc.meta.status,
									doc.meta.priority,
									doc.meta.size,
									doc.meta.target_area,
									doc.meta.milestone
								]
									.filter(Boolean)
									.join(' · ')}</span
							>
						</button>
					{/each}
					{#if !entries.length}<p>조건에 맞는 항목이 없습니다.</p>{/if}
				{/if}
			</aside>
			<main class="reading-content" use:linkNavigation>
				{#if view !== 'book' && selected}
					<div class="bundle-header">
						<h1>{selected.title}</h1>
						<p>{selected.meta.id} · {selected.meta.status ?? 'unknown'}</p>
						{#if taskChecks.total}<p>
								태스크 체크: {taskChecks.checked}/{taskChecks.total} — 검증·통합 상태는 해당 기록에서
								확인하세요.
							</p>{/if}
						{#if relations.length}<div class="relations">
								관련 문서: {#each relations as id}{#if ids.has(id)}<button
											onclick={() => onOpen(ids.get(id)!.path)}>{id}</button
										>{:else}<span>{id}</span>{/if}{/each}
							</div>{/if}
						<nav aria-label="번들 문서">
							{#each bundle as doc}<button
									class:active={detail?.path === doc.path}
									onclick={() => {
										detailPath = doc.path;
										currentAnchor = '';
										onLocation(doc.path, '', view, doc.meta);
									}}>{fileLabel(doc.path)}</button
								>{/each}
						</nav>
						{#if detail}<nav class="detail-toc" aria-label="문서 목차">
								{#each rendered.get(detail.path)?.headings ?? [] as h}<button
										onclick={() => jump(detail.path, h.id)}>{h.title}</button
									>{/each}
							</nav>{/if}
					</div>
				{/if}
				{#each visibleDocs as doc (doc.path)}
					<section class="chapter" id={documentAnchor(doc.path)} use:trackHeading>
						<header>
							<div>
								<span class="chapter-group">{bookGroup(doc) ?? fileLabel(doc.path)}</span>
								<h2>{doc.title}</h2>
								<small>{doc.meta.id ? doc.meta.id + ' · ' : ''}{doc.path}</small>
							</div>
							<button onclick={() => onOpen(doc.path)}>원본 보기</button>
						</header>
						{#key `${doc.path}-${branch}-${theme}-${doc.raw}`}
							<article class="markdown-body" use:lazyDiagrams use:trackHeading>
								{@html rendered.get(doc.path)?.html ?? ''}
							</article>
						{/key}
					</section>
				{/each}
				{#if !visibleDocs.length}<p class="empty">
						{view === 'book' ? '읽을 문서가 없습니다.' : '목록에서 항목을 선택하세요.'}
					</p>{/if}
			</main>
		</div>
	{/if}
</div>

<style>
	.knowledge {
		display: flex;
		flex-direction: column;
		min-height: 0;
		height: 100%;
		color: var(--text-primary);
	}
	.filters {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 10px;
		padding: 16px;
		border-bottom: 1px solid var(--border-panel);
	}
	label {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
	}
	button,
	input,
	select {
		font: inherit;
		color: var(--text-primary);
	}
	input,
	select {
		padding: 8px;
		border: 1px solid var(--border-input);
		background: var(--bg-input);
		border-radius: 6px;
	}
	button {
		cursor: pointer;
		border: 1px solid var(--border-panel);
		border-radius: 6px;
		background: var(--bg-panel);
		padding: 8px 10px;
		text-align: left;
	}
	button:hover,
	button.active {
		background: var(--tree-selected-bg);
		color: var(--tree-selected-text);
	}
	button:focus-visible,
	:global(.markdown-body a:focus-visible) {
		outline: 2px solid var(--tree-selected-text);
		outline-offset: 2px;
	}
	.reading-layout {
		display: grid;
		grid-template-columns: 280px minmax(0, 1fr);
		flex: 1;
		min-height: 0;
	}
	.outline {
		overflow: auto;
		padding: 16px;
		border-right: 1px solid var(--border-panel);
	}
	.outline h2 {
		font-size: 13px;
		color: var(--text-muted);
		margin: 22px 0 10px;
	}
	.outline button {
		display: block;
		width: 100%;
		border: 0;
		margin: 3px 0;
		background: transparent;
	}
	.outline button.active,
	.outline button:hover {
		background: var(--tree-selected-bg);
	}
	.subheading {
		font-size: 12px;
		color: var(--text-muted);
	}
	.entry {
		display: flex !important;
		flex-direction: column;
		gap: 6px;
		padding: 12px;
		border-bottom: 1px solid var(--border-panel) !important;
	}
	.entry span,
	.count {
		font-size: 12px;
		color: var(--text-muted);
	}
	.reading-content {
		overflow: auto;
		padding: 24px clamp(16px, 4vw, 64px);
		scroll-behavior: smooth;
	}
	.chapter {
		max-width: 960px;
		margin: 0 auto 48px;
		scroll-margin-top: 16px;
	}
	.chapter header {
		display: flex;
		justify-content: space-between;
		align-items: start;
		gap: 16px;
		padding-bottom: 20px;
		border-bottom: 1px solid var(--border-panel);
	}
	.chapter h2 {
		font-size: 24px;
		margin: 8px 0;
	}
	.chapter small,
	.chapter-group {
		color: var(--text-muted);
		overflow-wrap: anywhere;
	}
	.chapter-group {
		font-size: 12px;
	}
	.markdown-body {
		line-height: 1.8;
		overflow-wrap: anywhere;
		content-visibility: auto;
		contain-intrinsic-size: auto 600px;
	}
	.markdown-body :global([id]) {
		scroll-margin-top: 16px;
	}
	.markdown-body :global(a) {
		color: var(--tree-selected-text);
	}
	.markdown-body :global(pre) {
		overflow: auto;
		background: var(--pre-bg);
		padding: 16px;
		border: 1px solid var(--pre-border);
		border-radius: 8px;
	}
	.markdown-body :global(code) {
		font-size: 0.9em;
		color: var(--code-color);
	}
	.markdown-body :global(table) {
		display: block;
		overflow: auto;
		border-collapse: collapse;
	}
	.markdown-body :global(th),
	.markdown-body :global(td) {
		border: 1px solid var(--table-border);
		padding: 8px 12px;
	}
	.markdown-body :global(img),
	.markdown-body :global(svg) {
		max-width: 100%;
		height: auto;
	}
	.markdown-body :global(blockquote) {
		border-left: 3px solid var(--border-panel);
		margin-left: 0;
		padding-left: 16px;
		color: var(--text-muted);
	}
	.bundle-header {
		max-width: 960px;
		margin: 0 auto 24px;
	}
	.bundle-header nav,
	.relations {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin: 16px 0;
		align-items: center;
	}
	.detail-toc button {
		font-size: 12px;
	}
	.index-errors {
		padding: 12px 16px;
		color: var(--text-secondary);
	}
	.index-errors p {
		font-size: 12px;
		overflow-wrap: anywhere;
	}
	.empty {
		text-align: center;
		margin: 80px 0;
		color: var(--text-muted);
	}
	@media (max-width: 760px) {
		.reading-layout {
			grid-template-columns: 200px minmax(0, 1fr);
		}
		.reading-content {
			padding: 16px;
		}
	}
	@media (max-width: 520px) {
		.reading-layout {
			grid-template-columns: 1fr;
			grid-template-rows: 180px minmax(0, 1fr);
		}
		.outline {
			border-right: 0;
			border-bottom: 1px solid var(--border-panel);
		}
	}
</style>
