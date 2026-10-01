"""Who owns which entity tag, and what a push may do about it.

A bound entity's tags come from two owners:
- `framework_tags` mirror the framework's schema file (schema.yml / @bruin
  block) and are refreshed by reconcile — the framework owns them.
- `ui_tags` are added in the Trellis tag editor — the user owns them.

`pushed_tags` is the backend-owned record of which tags Trellis itself put
into the schema file. It is written only after a push, never by the frontend,
and it is the only thing that lets a push remove a tag: a push may remove a
tag only if Trellis pushed it and the user has since dropped it from
`ui_tags`. A tag the framework already carried is never recorded as pushed, so
it can never be removed from Trellis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trellis_datamodel.models.entity_keys import get_framework_tags, get_model_ref

PUSHED_TAGS_KEY = "pushed_tags"


@dataclass(frozen=True)
class TagPushPlan:
    """What one push does to a schema entry's tags.

    `to_add`/`to_remove` are applied to the live tag list; `pushed_tags` is
    the record to persist for the next push.
    """

    to_add: list[str]
    to_remove: list[str]
    pushed_tags: list[str]

    def apply(self, live_tags: list[str]) -> list[str]:
        """The tag list after this push, keeping the live order."""
        return [tag for tag in live_tags if tag not in self.to_remove] + self.to_add


def plan_tag_push(
    ui_tags: list[str] | None,
    pushed_tags: list[str] | None,
    live_tags: list[str],
) -> TagPushPlan | None:
    """Plan a push of `ui_tags` onto a schema entry currently carrying `live_tags`.

    Returns None when `ui_tags` is None: Trellis has no opinion this push, so
    nothing is added, removed, or re-recorded. An explicit `[]` removes every
    tag Trellis pushed. `pushed_tags=None` (never pushed, or a file written
    before this field existed) removes nothing.
    """
    if ui_tags is None:
        return None

    wanted = list(dict.fromkeys(ui_tags))
    previously_pushed = set(pushed_tags or [])
    dropped = previously_pushed - set(wanted)
    live = set(live_tags)

    return TagPushPlan(
        to_add=[tag for tag in wanted if tag not in live],
        to_remove=[tag for tag in live_tags if tag in dropped],
        # Already-pushed tags stay ours; a tag the framework carried before
        # this push is the framework's, never ours.
        pushed_tags=[
            tag for tag in wanted if tag in previously_pushed or tag not in live
        ],
    )


def reconcile_entity_tags(
    existing_tags: list[str],
    manifest_tags: list[str] | None,
) -> list[str]:
    """The active framework is authoritative for the mirrored `framework_tags` field.
    manifest_tags=None -> model absent from manifest, non-destructive (unchanged).
    manifest_tags=[] (present, no tags) -> mirrored tags cleared.
    """
    if manifest_tags is None:
        return existing_tags
    return list(manifest_tags)


def compute_display_tags(entity: dict[str, Any]) -> list[str]:
    """The tag list to show/export for an entity — never persisted.

    Bound entities: the union of `framework_tags` (framework-owned,
    reconcile-refreshed) and `ui_tags` (user-added via the Trellis tag
    editor), deduplicated, framework_tags first. Unbound entities have no
    schema.yml to mirror — `tags` is their single, freely-editable,
    already-authoritative field.
    """
    if get_model_ref(entity):
        framework_tags = get_framework_tags(entity)
        ui_tags = entity.get("ui_tags") or []
        seen: set[str] = set()
        result: list[str] = []
        for tag in [*framework_tags, *ui_tags]:
            if tag not in seen:
                seen.add(tag)
                result.append(tag)
        return result
    return entity.get("tags") or []


def migrate_legacy_tags(entity: dict[str, Any], framework_tags: list[str]) -> bool:
    """Retire a bound entity's legacy `tags` key; return True if it existed.

    One-time migration: a bound entity's legacy `tags` value (from before the
    framework_tags/ui_tags split existed) is folded into ui_tags ONLY if it
    represents real legacy/user-curated data — i.e. it differs from what
    framework reconciliation says right now (`framework_tags`). A value that
    already matches is the framework's own tag list from an earlier run under
    the old field name, not something the user added, and must NOT be copied
    into ui_tags (that would wrongly mark the framework's tags as
    Trellis-authored and defeat the read-only/removable UI split). The legacy
    `tags` key itself is always retired afterward — bound entities never
    persist `tags` going forward, only framework_tags/ui_tags.
    """
    if "tags" not in entity:
        return False
    legacy_tags = entity.get("tags") or []
    if "ui_tags" not in entity and legacy_tags and legacy_tags != framework_tags:
        entity["ui_tags"] = list(legacy_tags)
    del entity["tags"]
    return True
