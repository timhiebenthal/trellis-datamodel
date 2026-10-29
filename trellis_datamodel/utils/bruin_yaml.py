"""Shared ruamel round-trip YAML for Bruin asset definitions.

The reader (:mod:`bruin_parser`) and the writer (:mod:`bruin_rewriter`) have to
agree on how strings are quoted, or a parse -> modify -> write -> re-parse trip
can change a field's value. They historically disagreed: the reader used PyYAML
(YAML 1.1) while the writer used ruamel (YAML 1.2), and a plain string like
``yes`` written by ruamel was read back by PyYAML as the boolean ``True``.

Both sides now build their YAML from :func:`bruin_yaml` so the settings cannot
drift apart again.
"""

from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.representer import RoundTripRepresenter
from yaml.nodes import ScalarNode
from yaml.resolver import Resolver as _PyYamlResolver

from trellis_datamodel.utils.yaml_handler import round_trip_yaml

_STR_TAG = "tag:yaml.org,2002:str"

# PyYAML's own implicit resolver, i.e. the YAML 1.1 rules the parser reads with.
_pyyaml_resolver = _PyYamlResolver()


def _plain_would_be_coerced(value: str) -> bool:
    """Whether a YAML 1.1 reader would read *value* left unquoted as anything
    other than this same string.

    ruamel resolves with YAML 1.2, where ``yes``/``no``/``on``/``off`` and
    base-60 numbers such as ``1:30`` are plain strings. PyYAML resolves those
    as booleans and integers, so writing them unquoted silently rewrites the
    value on the next read. Asking PyYAML's resolver directly keeps this
    aligned with the reader without hand-copying its regexes.
    """
    return _pyyaml_resolver.resolve(ScalarNode, value, (True, False)) != _STR_TAG


class _BruinRepresenter(RoundTripRepresenter):
    """Round-trip representer that quotes strings a YAML 1.1 reader would
    misread, and leaves every other scalar byte-identical.

    A quoted scalar loaded round-trip is a ``ScalarString`` subclass with its
    own representer, so this only sees plain ``str`` values - from the API or
    from newly drafted fields - which carry no quote style of their own.
    """

    def represent_str(self, data: Any) -> Any:
        if _plain_would_be_coerced(data):
            return self.represent_scalar(_STR_TAG, data, style="'")
        return self.represent_scalar(_STR_TAG, data)


_BruinRepresenter.add_representer(str, _BruinRepresenter.represent_str)


def bruin_yaml() -> YAML:
    """The shared round-trip YAML (:func:`round_trip_yaml`) set up for Bruin.

    ``preserve_quotes`` keeps a user's quoting on scalars that came from a
    round-trip load; the custom representer covers the plain strings that did
    not. Values that cannot be carried as style (they cross the JSON API) are
    quoted by the representer instead of being silently coerced. PyYAML
    accepts duplicate keys (last one wins), so the reader stays tolerant of
    files ruamel would otherwise reject.
    """
    return round_trip_yaml(representer=_BruinRepresenter, allow_duplicate_keys=True)
