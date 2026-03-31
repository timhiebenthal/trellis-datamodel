<script lang="ts">
	let { position }: { position: 'before' | 'after' } = $props();
</script>

<div
	class="absolute left-0 right-0 h-0.5 bg-primary-500 z-10"
	class:-top-1={position === 'before'}
	class:-bottom-1={position === 'after'}
>
	<div class="absolute -left-1 -top-1 w-2 h-2 bg-primary-500 rounded-full"></div>
	<div class="absolute -right-1 -top-1 w-2 h-2 bg-primary-500 rounded-full"></div>
</div>
