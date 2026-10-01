"""Characterization tests for the shared FK placement rule."""

import pytest

from trellis_datamodel.services.fk_placement import FkPlacement, place_foreign_key

FK_ON_TARGET = [
    "one_to_many",
    "one_to_zero_or_many",
    "zero_or_one_to_many",
    "zero_or_many_to_many",
]
# many_to_many on source vs zero_or_many_to_many on target is existing behaviour.
FK_ON_SOURCE = ["many_to_one", "many_to_many", "zero_or_many_to_one", "one_to_one"]


@pytest.mark.parametrize("rel_type", FK_ON_TARGET + ["unknown_type", ""])
def test_fk_on_target(rel_type):
    assert place_foreign_key(rel_type, "src", "sf", "tgt", "tf") == FkPlacement(
        fk_entity="tgt", fk_field="tf", ref_entity="src", ref_field="sf"
    )


@pytest.mark.parametrize("rel_type", FK_ON_SOURCE)
def test_fk_on_source(rel_type):
    assert place_foreign_key(rel_type, "src", "sf", "tgt", "tf") == FkPlacement(
        fk_entity="src", fk_field="sf", ref_entity="tgt", ref_field="tf"
    )
