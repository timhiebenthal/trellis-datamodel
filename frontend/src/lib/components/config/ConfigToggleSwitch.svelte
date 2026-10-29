<script lang="ts">
    let {
        id,
        checked,
        onchange,
        disabled = false,
    }: {
        id: string;
        checked: boolean;
        onchange: (checked: boolean) => void;
        disabled?: boolean;
    } = $props();
</script>

<label class="relative inline-flex items-center cursor-pointer">
    <input
        {id}
        type="checkbox"
        {checked}
        onchange={(e) => onchange(e.currentTarget.checked)}
        {disabled}
        class="sr-only peer focus:ring-0 focus:ring-offset-0"
    />
    <div class="w-11 h-6 bg-gray-200 rounded-full peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500 peer-checked:bg-primary-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full {disabled ? 'opacity-50' : ''}"></div>
</label>
