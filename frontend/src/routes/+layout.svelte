<script lang="ts">
	import '@xyflow/svelte/dist/style.css';
	import '../app.css';
	import logoHref from '$lib/assets/trellis_squared.svg?url';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" type="image/svg+xml" href={logoHref} />
</svelte:head>

{@render children()}
