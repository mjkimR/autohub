import { expect, test, vi, afterEach } from 'vitest';
import { waitFor } from '@testing-library/svelte';
import { diagrams } from './diagrams';
const { renderer } = vi.hoisted(() => ({ renderer: { initialize: vi.fn(), render: vi.fn() } }));
vi.mock('mermaid', () => ({ default: renderer }));
afterEach(() => {
	document.body.replaceChildren();
	vi.clearAllMocks();
});
function article() {
	const node = document.createElement('article');
	node.innerHTML = '<pre><code class="language-mermaid">flowchart LR; A-->B</code></pre>';
	document.body.append(node);
	return node;
}
test.each([true, false])('diagrams follow Hub theme dark=%s and sanitize SVG', async (dark) => {
	renderer.render.mockImplementation(async (_id, _text, container: HTMLElement) => {
		expect(container.hidden).toBe(false);
		expect(container.classList.contains('invisible')).toBe(true);
		return {
			svg: '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><script>alert(1)</script><text>Safe diagram</text></svg>'
		};
	});
	const node = article();
	const action = diagrams(node, { html: node.innerHTML, dark });
	await waitFor(() => expect(node.querySelector('figure')).toBeTruthy());
	expect(renderer.initialize).toHaveBeenCalledWith(
		expect.objectContaining({ securityLevel: 'strict', theme: dark ? 'dark' : 'neutral' })
	);
	expect(node.querySelector('script,[onload]')).toBeNull();
	expect(node.textContent).toContain('Safe diagram');
	action.destroy();
});
test('invalid diagrams keep source and an explicit explanation', async () => {
	renderer.render.mockRejectedValue(new Error('Invalid syntax'));
	const node = article();
	const action = diagrams(node, { html: node.innerHTML, dark: false });
	await waitFor(() => expect(node.textContent).toContain('Diagram unavailable'));
	expect(node.querySelector('code')?.textContent).toContain('A-->B');
	action.destroy();
});
test('destroyed diagrams cannot publish a late render', async () => {
	let finish!: (value: { svg: string }) => void;
	renderer.render.mockImplementation(
		() =>
			new Promise((resolve) => {
				finish = resolve;
			})
	);
	const node = article();
	const action = diagrams(node, { html: node.innerHTML, dark: false });
	await waitFor(() => expect(finish).toBeTypeOf('function'));
	action.destroy();
	finish({ svg: '<svg><text>Late</text></svg>' });
	await Promise.resolve();
	await Promise.resolve();
	expect(node.querySelector('figure')).toBeNull();
});
