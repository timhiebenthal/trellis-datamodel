import { normalizeTags } from '$lib/utils';

export function mapEntityTagsToNodeData(entity: { dbt_model?: string; tags?: unknown; trellis_tags?: unknown }): {
    tags: string[];
    trellis_tags: string[];
} {
    const tags = normalizeTags(entity.tags);
    if (!entity.dbt_model) {
        return { tags, trellis_tags: tags };
    }
    return { tags, trellis_tags: normalizeTags(entity.trellis_tags) };
}
