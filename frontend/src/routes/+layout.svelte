<script lang="ts">
	import '../app.css';
	import '@xyflow/svelte/dist/style.css';
	import logoHref from '$lib/assets/trellis_squared.svg?url';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" type="image/svg+xml" href={logoHref} />
</svelte:head>

{@render children()}
