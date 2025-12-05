<script lang="ts">
	import '../app.css';
	import '@xyflow/svelte/dist/style.css';
	import { assets } from '$app/paths';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" type="image/svg+xml" href={`${assets}/trellis_squared.svg`} />
</svelte:head>

{@render children()}
