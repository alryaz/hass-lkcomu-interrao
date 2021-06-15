__all__ = (
    "CONFIG_ENTRY_SCHEMA",
    "ENTITY_CODES_VALIDATORS",
    "ENTITY_CONF_VALIDATORS",
)

from datetime import timedelta
from typing import Any, Callable, Collection, Hashable, Mapping, Optional, TypeVar, Union

import voluptuous as vol
from homeassistant.const import (
    CONF_DEFAULT,
    CONF_ENTITIES,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TYPE,
    CONF_USERNAME,
)
from homeassistant.helpers import config_validation as cv

from custom_components.lkcomu_interrao.const import (
    API_TYPE_DEFAULT,
    API_TYPE_NAMES,
    CONF_ACCOUNTS,
    CONF_FILTER,
    CONF_INVOICES,
    CONF_METERS,
    CONF_NAME_FORMAT,
    CONF_USER_AGENT,
    DEFAULT_NAME_FORMAT_ACCOUNTS,
    DEFAULT_NAME_FORMAT_INVOICES,
    DEFAULT_NAME_FORMAT_METERS,
    DEFAULT_SCAN_INTERVAL,
)

TValidated = TypeVar("TValidated")
TCodeIndex = TypeVar("TCodeIndex", bound=Hashable)
EntityOptionsDict = Mapping[str, Mapping[Union[TCodeIndex, str], TValidated]]
TFiltered = TypeVar("TFiltered")
MIN_SCAN_INTERVAL = timedelta(seconds=60)


class _SubValidated(dict):
    def __getitem__(self, item: str):
        if item not in self:
            return dict.__getitem__(self, CONF_DEFAULT)
        return dict.__getitem__(self, item)


def _validator_single(val_validator: Callable[[Any], TValidated], idx_keys: Collection[str]):
    if idx_keys is None:
        idx_keys = tuple(ENTITY_CODES_VALIDATORS.keys())
    elif not isinstance(idx_keys, tuple):
        idx_keys = tuple(idx_keys)

    return vol.All(val_validator, lambda x: dict.fromkeys(idx_keys, x))


def _validator_multi(
    val_validator: Callable[[Any], TValidated],
    val_defaults: Mapping[str, TValidated],
    idx_keys: Collection[str],
):
    if idx_keys is None:
        idx_keys = tuple(ENTITY_CODES_VALIDATORS.keys())
    elif not isinstance(idx_keys, tuple):
        idx_keys = tuple(idx_keys)

    single_validator = _validator_single(val_validator, idx_keys)
    multi_validator = vol.Schema(
        {vol.Optional(key, default=val_defaults[key]): val_validator for key in idx_keys}
    )

    if val_validator is cv.boolean:
        multi_validator = vol.Any(
            multi_validator,
            vol.All(
                [vol.Any(vol.Equal(CONF_DEFAULT), vol.In(idx_keys))],
                vol.Any(
                    vol.All(
                        vol.Contains(CONF_DEFAULT),
                        lambda x: {key: (key not in x) for key in idx_keys},
                    ),
                    lambda x: {key: (key in x) for key in idx_keys},
                ),
            ),
        )

    return vol.All(vol.Any(single_validator, lambda x: x), multi_validator)


def _validator_codes(
    val_validator: Callable[[Any], TValidated],
    val_default: Any,
    code_validator: Callable[[Any], TCodeIndex],
):
    schema_validator = vol.Schema(
        {
            vol.Optional(CONF_DEFAULT, default=val_default): val_validator,
            code_validator: val_validator,
        }
    )

    if val_validator is cv.boolean:
        schema_validator = vol.Any(
            schema_validator,
            vol.All(
                [vol.Any(vol.Equal(CONF_DEFAULT), code_validator)],
                vol.Any(
                    vol.All(
                        vol.Contains(CONF_DEFAULT),
                        lambda x: {**dict.fromkeys(x, False), CONF_DEFAULT: True},
                    ),
                    lambda x: {**dict.fromkeys(x, True), CONF_DEFAULT: False},
                ),
            ),
        )

    return vol.All(schema_validator, vol.Coerce(_SubValidated))


def _validator_granular(
    val_validator: Callable[[Any], TValidated],
    val_defaults: Mapping[str, TValidated],
    idx_validators: Optional[Mapping[str, Callable[[Any], TCodeIndex]]] = None,
) -> Callable[[Any], EntityOptionsDict]:
    if idx_validators is None:
        idx_validators = ENTITY_CODES_VALIDATORS

    multi_validator = _validator_multi(val_validator, val_defaults, idx_validators.keys())
    granular_validator = vol.Schema(
        {
            vol.Optional(
                key, default=_SubValidated({CONF_DEFAULT: val_defaults[key]})
            ): _validator_codes(val_validator, val_defaults[key], code_validator)
            for key, code_validator in idx_validators.items()
        }
    )

    return vol.All(
        vol.Any(
            vol.All(
                multi_validator,
                lambda x: {sub_key: {CONF_DEFAULT: value} for sub_key, value in x.items()},
            ),
            lambda x: x,
        ),
        granular_validator,
    )


ENTITY_CODES_VALIDATORS = {
    CONF_ACCOUNTS: cv.string,
    CONF_INVOICES: cv.string,
    CONF_METERS: cv.string,
}

SINGLE_LEVEL_OPTIONS_SCHEMA_DICT = {
    vol.Optional(CONF_FILTER): _validator_codes(
        cv.boolean, True, ENTITY_CODES_VALIDATORS[CONF_ACCOUNTS]
    )
}

ENTITY_CONF_VALIDATORS = {
    # Validator for entity scan intervals
    CONF_SCAN_INTERVAL: _validator_granular(
        vol.All(cv.positive_time_period, vol.Clamp(min=MIN_SCAN_INTERVAL)),
        {
            # Same scan interval by default
            CONF_METERS: DEFAULT_SCAN_INTERVAL,
            CONF_ACCOUNTS: DEFAULT_SCAN_INTERVAL,
            CONF_INVOICES: DEFAULT_SCAN_INTERVAL,
        },
    ),
    # Validator for entity name formats
    CONF_NAME_FORMAT: _validator_granular(
        cv.string,
        {
            # Assign default name formats
            CONF_METERS: DEFAULT_NAME_FORMAT_METERS,
            CONF_ACCOUNTS: DEFAULT_NAME_FORMAT_ACCOUNTS,
            CONF_INVOICES: DEFAULT_NAME_FORMAT_INVOICES,
        },
    ),
    # Validator for entity filtering
    CONF_ENTITIES: _validator_granular(
        cv.boolean,
        {
            # Enable all entities by default
            CONF_METERS: True,
            CONF_ACCOUNTS: True,
            CONF_INVOICES: True,
        },
    ),
}

MULTI_LEVEL_OPTIONS_SCHEMA_DICT = {
    vol.Optional(conf_key, default=validator({})): validator
    for conf_key, validator in ENTITY_CONF_VALIDATORS.items()
}

BASE_CONFIG_ENTRY_SCHEMA = vol.Schema(
    {
        # Primary API configuration
        vol.Optional(CONF_TYPE, default=API_TYPE_DEFAULT): vol.In(API_TYPE_NAMES),
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        # Additional API configuration
        vol.Optional(CONF_USER_AGENT): vol.All(
            cv.string, lambda x: " ".join(map(str.strip, x.split("\n")))
        ),
    },
    extra=vol.PREVENT_EXTRA,
)

CONFIG_ENTRY_SCHEMA = BASE_CONFIG_ENTRY_SCHEMA.extend(
    MULTI_LEVEL_OPTIONS_SCHEMA_DICT,
    extra=vol.PREVENT_EXTRA,
).extend(
    SINGLE_LEVEL_OPTIONS_SCHEMA_DICT,
    extra=vol.PREVENT_EXTRA,
)
