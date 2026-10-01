"""Unit tests for the tag ownership rules (services/tag_ownership.py).

Live tags here are shaped like the adapter actually reads them: the
deduplicated tag list already in the schema entry being written, before the
push mutates it.
"""

from trellis_datamodel.services.tag_ownership import (
    migrate_legacy_tags,
    plan_tag_push,
)


def _push(ui_tags, pushed_tags, live_tags):
    """Plan a push and return (resulting live tags, new pushed_tags record)."""
    plan = plan_tag_push(ui_tags, pushed_tags, live_tags)
    return plan.apply(live_tags), plan.pushed_tags


class TestPlanTagPush:
    def test_adds_new_ui_tag_and_records_it_as_pushed(self):
        assert _push(["pii"], None, ["nightly"]) == (["nightly", "pii"], ["pii"])

    def test_removes_a_previously_pushed_tag_dropped_from_ui_tags(self):
        assert _push(["gdpr"], ["pii", "gdpr"], ["nightly", "pii", "gdpr"]) == (
            ["nightly", "gdpr"],
            ["gdpr"],
        )

    def test_ui_tags_none_is_a_no_op(self):
        """No opinion this push: nothing added, nothing removed, record untouched."""
        assert plan_tag_push(None, ["pii"], ["nightly", "pii"]) is None

    def test_explicit_empty_ui_tags_removes_only_pushed_tags(self):
        assert _push([], ["pii"], ["nightly", "pii"]) == (["nightly"], [])

    def test_absent_pushed_tags_removes_nothing(self):
        """Files written before `pushed_tags` existed fall back to additive-only."""
        assert _push([], None, ["nightly", "pii"]) == (["nightly", "pii"], [])

    def test_ui_tag_already_native_is_not_recorded_as_pushed(self):
        live, pushed = _push(["nightly", "pii"], None, ["nightly"])
        assert live == ["nightly", "pii"]
        assert pushed == ["pii"]
        # ...so dropping it later never deletes the framework-native tag.
        assert _push(["pii"], pushed, live) == (["nightly", "pii"], ["pii"])

    def test_already_pushed_tag_stays_recorded_while_present(self):
        assert _push(["pii"], ["pii"], ["nightly", "pii"]) == (
            ["nightly", "pii"],
            ["pii"],
        )

    def test_never_removes_a_tag_outside_the_pushed_record(self):
        """Even a stale record naming tags the user never had cannot reach a
        live tag it does not list."""
        live, _ = _push([], ["pii"], ["nightly", "hourly", "pii"])
        assert live == ["nightly", "hourly"]

    def test_pushed_tag_removed_in_framework_is_re_added(self):
        """Known limitation: a still-wanted pushed tag deleted directly in the
        framework is written back (and kept in the record)."""
        assert _push(["pii"], ["pii"], ["nightly"]) == (["nightly", "pii"], ["pii"])

    def test_duplicate_ui_tags_are_pushed_once(self):
        assert _push(["pii", "pii"], None, []) == (["pii"], ["pii"])


class TestMigrateLegacyTags:
    def test_legacy_tags_differing_from_framework_seed_ui_tags(self):
        entity = {"id": "e", "tags": ["pii"]}
        assert migrate_legacy_tags(entity, ["nightly"]) is True
        assert entity == {"id": "e", "ui_tags": ["pii"]}

    def test_legacy_tags_equal_to_framework_tags_are_not_copied(self):
        """Canonical rule: the framework's own tags under the old field name are
        not Trellis-authored and must not become ui_tags."""
        entity = {"id": "e", "tags": ["nightly"]}
        assert migrate_legacy_tags(entity, ["nightly"]) is True
        assert entity == {"id": "e"}

    def test_existing_ui_tags_are_not_overwritten(self):
        entity = {"id": "e", "tags": ["pii"], "ui_tags": ["gdpr"]}
        migrate_legacy_tags(entity, [])
        assert entity == {"id": "e", "ui_tags": ["gdpr"]}

    def test_no_legacy_key_is_a_no_op(self):
        entity = {"id": "e", "ui_tags": ["pii"]}
        assert migrate_legacy_tags(entity, ["nightly"]) is False
        assert entity == {"id": "e", "ui_tags": ["pii"]}
