"""Validation behaviour of the business event pydantic models (checked via construction)."""

from datetime import datetime

import pytest
from pydantic import ValidationError as PydanticValidationError

from trellis_datamodel.exceptions import ValidationError
from trellis_datamodel.models.business_event import (
    AnnotationEntry,
    BusinessEventAnnotations,
    BusinessEventProcess,
    BusinessEventType,
    EntityDimensionMetadata,
)

NOW = datetime(2026, 1, 2, 3, 4, 5)


def _process(**overrides):
    fields = dict(
        id="proc_1",
        name="Order to cash",
        type=BusinessEventType.DISCRETE,
        domain="Sales",
        event_ids=["evt_1"],
        created_at=NOW,
        updated_at=NOW,
    )
    fields.update(overrides)
    return BusinessEventProcess(**fields)


def _annotations(**categories):
    return BusinessEventAnnotations(
        **{k: [AnnotationEntry(**e) for e in v] for k, v in categories.items()}
    )


class TestAnnotationEntryRole:
    def test_role_defaults_to_none(self):
        assert AnnotationEntry(id="a", text="customer").role is None

    def test_string_role_is_kept(self):
        assert AnnotationEntry(id="a", text="customer", role="buyer").role == "buyer"

    @pytest.mark.parametrize("bad_role", [5, ["buyer"], {"label": "buyer"}, True])
    def test_non_string_role_is_rejected_with_domain_validation_error(self, bad_role):
        with pytest.raises(ValidationError, match="role must be a string"):
            AnnotationEntry(id="a", text="customer", role=bad_role)


class TestUniqueEntryIds:
    def test_same_id_in_two_categories_is_rejected(self):
        with pytest.raises(PydanticValidationError, match="Duplicate entry IDs found.*dup"):
            _annotations(
                who=[{"id": "dup", "text": "customer"}],
                how_many=[{"id": "dup", "text": "revenue"}],
            )

    def test_same_id_twice_in_one_category_is_rejected(self):
        with pytest.raises(PydanticValidationError, match="Duplicate entry IDs"):
            _annotations(who=[{"id": "dup", "text": "a"}, {"id": "dup", "text": "b"}])

    def test_distinct_ids_are_accepted(self):
        ann = _annotations(who=[{"id": "a", "text": "x"}], what=[{"id": "b", "text": "x"}])

        assert (ann.who[0].id, ann.what[0].id) == ("a", "b")


class TestSupersetUniqueness:
    def test_distinct_entries_pass_and_return_same_object(self):
        ann = _annotations(who=[{"id": "a", "text": "customer"}, {"id": "b", "text": "seller"}])

        assert ann.validate_superset_uniqueness() is ann

    def test_same_dimension_in_same_category_is_a_duplicate(self):
        ann = _annotations(
            who=[
                {"id": "a", "text": "buyer", "dimension_id": "dim_c"},
                {"id": "b", "text": "client", "dimension_id": "dim_c"},
            ]
        )

        with pytest.raises(ValueError, match="who: 'client' \\(id: b\\) conflicts with 'buyer' \\(id: a\\)"):
            ann.validate_superset_uniqueness()

    def test_same_text_ignoring_case_and_whitespace_is_a_duplicate(self):
        ann = _annotations(
            what=[{"id": "a", "text": "Product"}, {"id": "b", "text": "  product "}]
        )

        with pytest.raises(ValueError, match="violate union uniqueness rules"):
            ann.validate_superset_uniqueness()

    def test_same_text_with_different_description_is_not_a_duplicate(self):
        ann = _annotations(
            what=[
                {"id": "a", "text": "product", "description": "physical"},
                {"id": "b", "text": "product", "description": "digital"},
            ]
        )

        assert ann.validate_superset_uniqueness() is ann

    def test_same_text_in_different_categories_is_not_a_duplicate(self):
        ann = _annotations(who=[{"id": "a", "text": "store"}], where=[{"id": "b", "text": "store"}])

        assert ann.validate_superset_uniqueness() is ann

    def test_same_dimension_in_different_categories_is_not_a_duplicate(self):
        ann = _annotations(
            who=[{"id": "a", "text": "x", "dimension_id": "dim"}],
            where=[{"id": "b", "text": "x", "dimension_id": "dim"}],
        )

        assert ann.validate_superset_uniqueness() is ann

    def test_every_conflict_is_listed_in_the_message(self):
        ann = _annotations(
            who=[{"id": "a", "text": "c"}, {"id": "b", "text": "c"}],
            why=[{"id": "d", "text": "g"}, {"id": "e", "text": "g"}],
        )

        with pytest.raises(ValueError) as exc:
            ann.validate_superset_uniqueness()

        message = str(exc.value)
        assert "who: 'c' (id: b)" in message and "why: 'g' (id: e)" in message


class TestEntityDimensionMetadata:
    def test_defaults(self):
        meta = EntityDimensionMetadata()

        assert (meta.is_dimension_from_business_event, meta.business_event_sources, meta.annotation_type) == (
            False,
            [],
            None,
        )

    @pytest.mark.parametrize("kind", ["who", "what", "when", "where", "how", "how_many", "why"])
    def test_each_annotation_category_is_accepted(self, kind):
        assert EntityDimensionMetadata(annotation_type=kind).annotation_type == kind

    def test_explicit_none_annotation_type_is_accepted(self):
        assert EntityDimensionMetadata(annotation_type=None).annotation_type is None

    def test_unknown_annotation_type_is_rejected_listing_valid_ones(self):
        with pytest.raises(PydanticValidationError, match="Invalid annotation_type 'whom'.*how, how_many"):
            EntityDimensionMetadata(annotation_type="whom")


class TestBusinessEventProcess:
    def test_active_process_without_events_is_rejected(self):
        with pytest.raises(PydanticValidationError, match="at least one event"):
            _process(event_ids=[])

    def test_resolved_process_may_have_no_events(self):
        assert _process(event_ids=[], resolved_at=NOW).event_ids == []

    def test_domain_is_trimmed(self):
        assert _process(domain="  Sales ").domain == "Sales"

    def test_blank_domain_is_rejected(self):
        with pytest.raises(PydanticValidationError, match="domain cannot be empty"):
            _process(domain="   ")

    def test_missing_domain_is_allowed(self):
        assert _process(domain=None).domain is None

    def test_unknown_type_is_rejected(self):
        with pytest.raises(PydanticValidationError):
            _process(type="sometimes")
