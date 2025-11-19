<script lang="ts">
	import '../app.css';
	import '@xyflow/svelte/dist/style.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{@render children()}
