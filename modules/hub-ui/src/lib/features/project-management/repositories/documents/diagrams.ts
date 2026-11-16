import DOMPurify from 'dompurify';

/** Keep readable Mermaid source when the renderer rejects a diagram. */
export function diagrams(node: HTMLElement, options: { html: string; dark: boolean }) {
	let generation = 0;
	async function update(current: typeof options) {
		const id = ++generation;
		const blocks = [...node.querySelectorAll<HTMLElement>('pre > code.language-mermaid')];
		if (!blocks.length) return;
		try {
			const { default: mermaid } = await import('mermaid');
			if (id !== generation) return;
			mermaid.initialize({
				startOnLoad: false,
				securityLevel: 'strict',
				theme: current.dark ? 'dark' : 'neutral',
				flowchart: { htmlLabels: false }
			});
			for (const block of blocks) {
				if (id !== generation) return;
				const sandbox = document.createElement('div');
				sandbox.hidden = true;
				document.body.append(sandbox);
				try {
					const { svg } = await mermaid.render(
						`hub-diagram-${crypto.randomUUID()}`,
						block.textContent || '',
						sandbox
					);
					if (id !== generation) return;
					const figure = document.createElement('figure');
					figure.setAttribute('aria-label', 'Mermaid diagram');
					figure.className = 'overflow-auto rounded-lg border bg-card p-4';
					figure.innerHTML = DOMPurify.sanitize(svg, {
						USE_PROFILES: { svg: true, svgFilters: true },
						ALLOW_DATA_ATTR: false
					});
					block.parentElement?.replaceWith(figure);
				} catch {
					if (id === generation) {
						const explanation = document.createElement('p');
						explanation.textContent = 'Diagram unavailable. Mermaid source is shown below.';
						block.parentElement?.before(explanation);
					}
				} finally {
					sandbox.remove();
				}
			}
		} catch {
			if (id === generation)
				for (const block of blocks)
					block.parentElement?.setAttribute(
						'title',
						'Diagram renderer unavailable; source retained'
					);
		}
	}
	void update(options);
	return {
		update: (value: typeof options) => {
			void update(value);
		},
		destroy: () => {
			generation++;
		}
	};
}
