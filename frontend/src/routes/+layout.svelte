<script lang="ts">
	import '../app.css';
	import '@xyflow/svelte/dist/style.css';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" type="image/svg+xml" href="/trellis_squared.svg" />
</svelte:head>

{@render children()}
