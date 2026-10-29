<script lang="ts">
	import Icon from '@iconify/svelte';
	import { getProcessesForRole as findProcessesForRole } from '$lib/utils/entity-detail';
	import type { EntityRole } from '$lib/types';
	import type { EntityDetailForm } from './entity-detail-form.svelte';

	let {
		form,
		entityId,
		onNavigateToProcess
	}: {
		form: EntityDetailForm;
		entityId: string;
		onNavigateToProcess: (processId: string) => void;
	} = $props();

	function getProcessesForRole(dimensionId: string, role: EntityRole) {
		return findProcessesForRole(form.processes, dimensionId, role);
	}
</script>

<div class="rounded-lg border border-gray-200 bg-white shadow-2xs overflow-hidden transition-all hover:border-gray-300" data-testid="roles-and-aliases">
	<button
		type="button"
		class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left bg-gray-50/70 hover:bg-gray-100/70 transition-colors"
		aria-expanded={form.showRolesSection}
		onclick={() => (form.showRolesSection = !form.showRolesSection)}
	>
		<span class="flex min-w-0 items-center gap-2">
			<Icon icon="lucide:users-round" class="h-4 w-4 shrink-0 text-primary-600" />
			<span class="text-sm font-semibold text-gray-800">Roles &amp; aliases</span>
			<span class="truncate text-xs text-gray-500 font-medium">
				{form.uniqueEntityRoles.length} {form.uniqueEntityRoles.length === 1 ? 'role' : 'roles'}
				{#if form.autoRoles.length > 0}
					· {form.autoRoles.length} {form.autoRoles.length === 1 ? 'alias' : 'aliases'}
				{/if}
			</span>
		</span>
		<span class="inline-flex shrink-0 items-center gap-1.5 px-2.5 py-1 text-xs font-semibold text-primary-700 bg-primary-50 hover:bg-primary-100 rounded-md border border-primary-200/70 transition-colors">
			{form.showRolesSection ? 'Hide details' : 'Manage'}
			<Icon icon={form.showRolesSection ? 'lucide:chevron-up' : 'lucide:chevron-down'} class="h-3.5 w-3.5" />
		</span>
	</button>

	{#if form.showRolesSection}
		<div class="border-t border-gray-200 p-4 space-y-4">
			<!-- Role aliases (read-only auto-generated) -->
			{#if form.autoRoles.length > 0}
				<div>
					<div class="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-500">Aliases</div>
					<div class="flex flex-wrap gap-1.5">
						{#each form.autoRoles as role}
							<span class="inline-flex max-w-full items-center gap-1.5 rounded-md border border-primary-200 bg-primary-50/80 px-2.5 py-1 text-xs text-primary-900 shadow-3xs" title={role.source ? `Source: ${role.source}` : undefined}>
								<Icon icon="lucide:link" class="h-3 w-3 shrink-0 text-primary-600" />
								<span class="truncate font-medium">{role.label || role.role}</span>
								{#if role.role && role.label}
									<span class="truncate text-primary-700">({role.role})</span>
								{/if}
								{#if role.source}
									<span class="truncate text-[10px] text-primary-600 font-normal">· {role.source}</span>
								{/if}
							</span>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Roles (for dimensions only) -->
			<div>
				<div class="flex items-center gap-2 mb-2.5">
					<label class="block text-xs font-semibold text-gray-700 uppercase tracking-wide">
						Roles ({form.uniqueEntityRoles.length})
					</label>
					<button
						type="button"
						class="text-gray-400 hover:text-gray-600 transition-colors"
						title="Role-playing dimensions: Track different contextual uses of the this dimension (e.g. 'date' can become 'order_date', 'ship_date', 'delivery_date')"
					>
						<Icon icon="lucide:info" class="w-3.5 h-3.5" />
					</button>
				</div>

				{#if form.uniqueEntityRoles.length === 0 && !form.roleInput}
					<!-- Empty state -->
					<p class="text-xs text-gray-400 italic py-1">No roles defined for this dimension. Use this functionality if this entity 'slips' into different roles and functions.</p>
				{:else}
					<!-- Role list -->
					<div class="border border-gray-200 rounded-lg overflow-hidden shadow-2xs">
						{#if form.uniqueEntityRoles.length > 0}
							<div class="divide-y divide-gray-100">
								{#each form.uniqueEntityRoles as role}
									<div class="border-b border-gray-100 last:border-b-0">
										<!-- Role header -->
										<div class="px-3.5 py-2.5 hover:bg-gray-50/80 transition-colors group flex items-center justify-between">
											<div class="flex items-center gap-2 flex-1">
												<button
													type="button"
													onclick={() => form.toggleRoleExpansion(role)}
													class="text-gray-400 hover:text-gray-600 transition-colors"
													title={form.expandedRoles.has(role.role || '') ? 'Collapse processes' : 'Expand to see processes'}
												>
													<Icon
														icon={form.expandedRoles.has(role.role || '') ? 'lucide:chevron-down' : 'lucide:chevron-right'}
														class="w-4 h-4"
													/>
												</button>

												{#if form.editingRoleName === role.role}
													<!-- Edit mode -->
													<input
														type="text"
														bind:value={form.editingRoleValue}
														onkeydown={form.handleEditRoleKeydown}
														onblur={form.saveEditingRole}
														class="flex-1 px-2.5 py-1 border border-primary-500 rounded-md text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
														placeholder="e.g., order_date, ship_date"
														autofocus
													/>
												{:else}
													<!-- View mode -->
													<button
														type="button"
														onclick={() => form.startEditingRole(role)}
														class="flex-1 text-left px-2 py-0.5 text-sm font-medium text-gray-900 hover:text-primary-700 transition-colors rounded"
														title="Click to edit"
													>
														{role.role}
													</button>
													<span class="text-xs text-gray-500 font-medium">
														({getProcessesForRole(entityId, role).length} processes)
													</span>
												{/if}
											</div>

											<div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
												<button
													type="button"
													onclick={() => form.startEditingRole(role)}
													class="p-1.5 text-gray-400 hover:text-primary-700 hover:bg-primary-50 rounded transition-colors"
													title="Edit role"
												>
													<Icon icon="lucide:pencil" class="w-3.5 h-3.5" />
												</button>
												<button
													type="button"
													onclick={() => form.confirmDeleteRole(role.role || '')}
													class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
													title="Delete role"
												>
													<Icon icon="lucide:trash-2" class="w-3.5 h-3.5" />
												</button>
											</div>
										</div>

										<!-- Expandable process list -->
										{#if form.expandedRoles.has(role.role || '')}
											<div class="px-4 pb-3 pl-12 bg-gray-50/70 border-t border-gray-100">
												{#each getProcessesForRole(entityId, role) as process}
													<button
														type="button"
														onclick={() => onNavigateToProcess(process.id)}
														class="block w-full text-left px-3 py-1.5 text-sm text-gray-700 hover:bg-white hover:text-primary-700 rounded-md transition-colors mb-1 last:mb-0 shadow-3xs"
													>
														<div class="flex items-center gap-2">
															<Icon icon="lucide:workflow" class="w-4 h-4 text-primary-600" />
															<span class="font-medium">{process.name}</span>
															<span class="text-xs text-gray-500">({process.event_ids.length} events)</span>
														</div>
													</button>
												{/each}

												{#if getProcessesForRole(entityId, role).length === 0}
													<p class="text-xs text-gray-500 italic px-3 py-1.5">
														No processes use this role yet
													</p>
												{/if}
											</div>
										{/if}
									</div>
								{/each}
							</div>
						{/if}
					</div>
				{/if}

				<!-- Add role input -->
				<div class="mt-3 flex gap-2">
					<input
						type="text"
						bind:value={form.roleInput}
						onkeydown={form.handleRoleInputKeydown}
						class="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm shadow-2xs focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all placeholder-gray-400"
						placeholder="e.g. Employee = Sales Agent, Manager, Team Lead, ..."
					/>
					<button
						type="button"
						onclick={form.addRole}
						disabled={!form.roleInput.trim()}
						class="px-3.5 py-1.5 text-xs font-semibold text-white bg-primary-600 hover:bg-primary-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 shadow-2xs transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
					>
						<Icon icon="lucide:plus" class="w-3.5 h-3.5" />
						Add Role
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
