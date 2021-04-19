"""Mosenergosbyt API"""
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Optional, Callable, Any, TypeVar, Mapping, Hashable, Union, Collection
from urllib.parse import quote

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD,
                                 CONF_SCAN_INTERVAL, CONF_DEFAULT, CONF_ENTITIES)
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import HomeAssistantType, ConfigType
from homeassistant.loader import bind_hass

from custom_components.mosenergosbyt.const import *

if TYPE_CHECKING:
    from custom_components.mosenergosbyt.api import API, Provider, ServiceType
    from custom_components.mosenergosbyt.sensor import MESAccountSensor

_LOGGER = logging.getLogger(__name__)

ENTITY_CODES_VALIDATORS = {
    CONF_ACCOUNTS: cv.string,
    CONF_INVOICES: cv.string,
    CONF_METERS: cv.string,
}

ENTITY_CONF_VALIDATORS = {}

TValidated = TypeVar('TValidated')
TCodeIndex = TypeVar('TCodeIndex', bound=Hashable)
EntityOptionsDict = Mapping[str, Mapping[Union[TCodeIndex, str], TValidated]]


class _SubValidated(dict):
    def __getitem__(self, item: str):
        if item not in self:
            return dict.__getitem__(self, CONF_DEFAULT)
        return dict.__getitem__(self, item)


def _validator_sub_values(val_validator: Callable[[Any], TValidated],
                          val_default: TValidated,
                          idx_validator: Callable[[Any], Hashable]):
    sub_validator = vol.Any(
        vol.All(
            vol.Schema({
                vol.Optional(CONF_DEFAULT, default=val_default): val_validator,
                idx_validator: val_validator
            }, extra=vol.PREVENT_EXTRA),
            _SubValidated
        ),
        vol.All(val_validator, lambda x: _SubValidated({CONF_DEFAULT: x}))
    )

    if val_validator is cv.boolean:
        sub_validator = vol.Any(
            sub_validator,
            vol.All(
                cv.ensure_list,
                [vol.Any(idx_validator, vol.Equal(CONF_DEFAULT))],
                lambda x: _SubValidated({CONF_DEFAULT: False, **{list_key: True for list_key in x}})
            )
        )

    return sub_validator


def _validator_sub_keys(val_validator: Callable[[Any], TValidated],
                        val_defaults: Mapping[str, TValidated],
                        idx_validators: Optional[Mapping[str, Callable[[Any], TCodeIndex]]] = None) \
        -> Callable[[Any], EntityOptionsDict]:
    if idx_validators is None:
        idx_validators = ENTITY_CODES_VALIDATORS

    singular_schema = vol.All(
        val_validator,
        lambda x: {gl_key: _SubValidated({CONF_DEFAULT: x}) for gl_key in val_defaults.keys()}
    )

    multiple_schema_dict = {}
    for sub_key in val_defaults.keys():
        val_default = val_defaults[sub_key]
        sub_validator = _validator_sub_values(val_validator, val_default, idx_validators[sub_key])
        key_schema = vol.Optional(sub_key, default=_SubValidated({CONF_DEFAULT: val_default}))
        multiple_schema_dict[key_schema] = sub_validator

    multiple_schema = vol.Schema(multiple_schema_dict)

    return vol.Any(singular_schema, multiple_schema)


TFiltered = TypeVar('TFiltered')

MIN_SCAN_INTERVAL = timedelta(seconds=60)


def _clamp_time_interval(value: timedelta):
    if value < MIN_SCAN_INTERVAL:
        _LOGGER.warning('Configured scan interval of %s is too low, clamped automatically to %s',
                        value, MIN_SCAN_INTERVAL)
        value = MIN_SCAN_INTERVAL

    return value


# Validator for entity scan intervals
ENTITY_CONF_VALIDATORS[CONF_SCAN_INTERVAL] = _validator_sub_keys(
    vol.All(cv.positive_time_period, _clamp_time_interval),
    {
        # Same scan interval by default
        CONF_METERS: DEFAULT_SCAN_INTERVAL,
        CONF_ACCOUNTS: DEFAULT_SCAN_INTERVAL,
        CONF_INVOICES: DEFAULT_SCAN_INTERVAL,
    }
)

# Validator for entity name formats
ENTITY_CONF_VALIDATORS[CONF_NAME_FORMAT] = _validator_sub_keys(
    cv.string,
    {
        # Assign default name formats
        CONF_METERS: DEFAULT_NAME_FORMAT_METERS,
        CONF_ACCOUNTS: DEFAULT_NAME_FORMAT_ACCOUNTS,
        CONF_INVOICES: DEFAULT_NAME_FORMAT_INVOICES,
    }
)

# Validator for entity filtering
ENTITY_CONF_VALIDATORS[CONF_ENTITIES] = _validator_sub_keys(
    cv.boolean,
    {
        # Enable all entities by default
        CONF_METERS: True,
        CONF_ACCOUNTS: True,
        CONF_INVOICES: True,
    }
)

BASE_CONFIG_ENTRY_SCHEMA = vol.Schema(
    {
        # Primary API configuration
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,

        # Additional API configuration
        vol.Optional(CONF_USER_AGENT): vol.All(cv.string, lambda x: ' '.join(map(str.strip, x.split('\n')))),
    },
    extra=vol.PREVENT_EXTRA
)

# Inner configuration schema (per-entry)
CONFIG_ENTRY_SCHEMA = BASE_CONFIG_ENTRY_SCHEMA.extend(
    {
        # Account-related filtering
        vol.Optional(CONF_FILTER): _validator_sub_values(cv.boolean, True, ENTITY_CODES_VALIDATORS[CONF_ACCOUNTS]),
    },
    extra=vol.PREVENT_EXTRA

).extend(
    {
        # Entity-related configuration
        vol.Optional(conf_key, default=validator({})): validator
        for conf_key, validator in ENTITY_CONF_VALIDATORS.items()
    },
    extra=vol.PREVENT_EXTRA
)


# Previous versions compatibility layer
def _adapt_old_config_entry_schema(options: Mapping[str, Any]):
    _LOGGER.warning('You are using a deprecated configuration format for username "%s"! Configuration '
                    'format used in 0.2.* is deprecated in 0.3.*, and will be removed in 0.3.5!',
                    options[CONF_USERNAME])

    new_options = {CONF_USERNAME: options[CONF_USERNAME],
                   CONF_PASSWORD: options[CONF_PASSWORD]}

    if CONF_USER_AGENT in options:
        new_options[CONF_USER_AGENT] = options[CONF_USER_AGENT]

    name_format = {}
    for new_key, old_key in {
        CONF_ACCOUNTS: 'account_name',
        CONF_METERS: 'meter_name',
        CONF_INVOICES: 'invoice_name',
    }.items():
        if old_key in options:
            name_format[new_key] = options[old_key]

    if name_format:
        new_options[CONF_NAME_FORMAT] = name_format

    if CONF_SCAN_INTERVAL in options:
        new_options[CONF_SCAN_INTERVAL] = options[CONF_SCAN_INTERVAL]

    entities = {}

    if CONF_INVOICES in options:
        if isinstance(options[CONF_INVOICES], list):
            entities[CONF_INVOICES] = {CONF_DEFAULT: False}
            entities[CONF_INVOICES].update({
                code: True
                for code in options[CONF_INVOICES]
            })

        else:
            entities[CONF_INVOICES] = {CONF_DEFAULT: options[CONF_INVOICES]}

    if CONF_ACCOUNTS in options:
        if isinstance(options[CONF_ACCOUNTS], list):
            entities[CONF_ACCOUNTS] = {CONF_DEFAULT: False}
            entities[CONF_ACCOUNTS].update({
                code: True
                for code in options[CONF_ACCOUNTS]
            })

        elif isinstance(options[CONF_ACCOUNTS], bool):
            entities[CONF_ACCOUNTS] = {CONF_DEFAULT: options[CONF_ACCOUNTS]}

        elif isinstance(options[CONF_ACCOUNTS], Mapping):
            entities[CONF_ACCOUNTS] = {CONF_DEFAULT: False}
            for code, value in options[CONF_ACCOUNTS].items():
                if value is False:
                    entities[CONF_ACCOUNTS][code] = False
                else:
                    entities[CONF_ACCOUNTS][code] = True

                    if isinstance(value, list):
                        if CONF_METERS not in entities:
                            entities[CONF_METERS] = {CONF_DEFAULT: False}

                        for meter_code in value:
                            entities[CONF_METERS][meter_code] = True

    return CONFIG_ENTRY_SCHEMA(new_options)


OLD_CONFIG_ENTRY_SCHEMA = vol.All(
    BASE_CONFIG_ENTRY_SCHEMA.extend(
        {
            # Old name formatting validation
            vol.Optional('account_name', default=DEFAULT_NAME_FORMAT_ACCOUNTS): cv.string,
            vol.Optional('meter_name', default=DEFAULT_NAME_FORMAT_METERS): cv.string,
            vol.Optional('invoice_name', default=DEFAULT_NAME_FORMAT_INVOICES): cv.string,

            # Old scan interval validation
            vol.Optional(CONF_SCAN_INTERVAL): cv.positive_time_period,

            # Old invoices schema
            vol.Optional(CONF_INVOICES): vol.Any(
                cv.boolean,
                vol.All(cv.ensure_list, [cv.string])
            ),

            # Old accounts schema
            vol.Optional(CONF_ACCOUNTS): vol.Any(
                vol.All(cv.ensure_list, [cv.string]),
                {cv.string: vol.Any(
                    vol.All(cv.ensure_list, [cv.string]),
                    vol.All(cv.boolean, True)
                )}
            ),
        }
    ),
    _adapt_old_config_entry_schema,
)

# Outer configuration schema (per-domain)
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(cv.ensure_list, [vol.Any(CONFIG_ENTRY_SCHEMA, OLD_CONFIG_ENTRY_SCHEMA)], vol.Length(min=1))
    },
    extra=vol.ALLOW_EXTRA,
)


@callback
def _find_existing_entry(hass: HomeAssistantType, username: str) -> Optional[config_entries.ConfigEntry]:
    existing_entries = hass.config_entries.async_entries(DOMAIN)
    for config_entry in existing_entries:
        if config_entry.data[CONF_USERNAME] == username:
            return config_entry


async def async_setup(hass: HomeAssistantType, config: ConfigType):
    """Set up the Mosenergosbyt component."""
    domain_config = config.get(DOMAIN)
    if not domain_config:
        return True

    domain_data = {}
    hass.data[DOMAIN] = domain_data

    yaml_config = {}
    hass.data[DATA_YAML_CONFIG] = yaml_config

    for user_cfg in domain_config:

        username = user_cfg[CONF_USERNAME]

        _LOGGER.debug('User "%s" entry from YAML' % username)

        existing_entry = _find_existing_entry(hass, username)
        if existing_entry:
            if existing_entry.source == config_entries.SOURCE_IMPORT:
                yaml_config[username] = user_cfg
                _LOGGER.debug('Skipping existing import binding')
            else:
                _LOGGER.warning('YAML config for user %s is overridden by another config entry!' % username)
            continue

        if username in yaml_config:
            _LOGGER.warning('User "%s" set up multiple times. Check your configuration.' % username)
            continue

        yaml_config[username] = user_cfg

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data={CONF_USERNAME: username},
            )
        )

    if yaml_config:
        _LOGGER.debug('YAML usernames: %s', '"' + '", "'.join(yaml_config.keys()) + '"')
    else:
        _LOGGER.debug('No configuration added from YAML')

    return True


@bind_hass
@callback
def async_handle_unsupported_accounts(hass: HomeAssistantType, username: str,
                                      unsupported_accounts: Collection[Mapping[str, Any]]):
    from custom_components.mosenergosbyt.api import Provider, ServiceType

    singular = len(unsupported_accounts) == 1
    message = f"Интеграция Мосэнергосбыт столкнулась с данными об " \
              f"аккаунт{'е' if singular else 'ах'}, " \
              f"которы{'й' if singular else 'е'} она не поддерживает.\n\n" \
              f"Пожалуйста, свяжитесь с разработчиком, чтобы добавить поддержку " \
              f"следующ{'его' if singular else 'их'} аккаунт{'а' if singular else 'ов'}:"

    for x in unsupported_accounts:
        service_type_id = int(x.get('kd_service_type', -1))
        service_type = ServiceType(service_type_id)
        provider_id = int(x.get('kd_provider', -1))
        provider = Provider(provider_id)

        github_issue_title = f'Поддержка аккаунта: _{provider.name} ({provider_id})_'
        github_issue_body = f'Прошу внедрить поддержку аккаунта типа ' \
                            f'_{provider.name}_ (`kd_provider == {provider_id}`).'
        github_issue_url = f'https://github.com/alryaz/hass-mosenergosbyt/issues/new' \
                           f'?body={quote(github_issue_body)}&title={quote(github_issue_title)}'
        message += f"\n" \
                   f"- **Номер л/с:** `{x.get('nn_ls', 'неизвестный')}`\n" \
                   f"  **Тип:** `{provider.name} ({provider_id}) / {service_type.name} ({service_type_id})`\n" \
                   f"  **GitHub:** [Создать Issue]({github_issue_url})"

    hass.components.persistent_notification.async_create(
        message,
        title=f"Мосэнергосбыт: Поддержка аккаунтов ({username})",
        notification_id=f"mosenergosbyt_unsupported_{username}",
    )


async def async_setup_entry(hass: HomeAssistantType, config_entry: config_entries.ConfigEntry):
    username = config_entry.data[CONF_USERNAME]

    # Check if leftovers from previous setup are present
    if username in hass.data.get(DATA_FINAL_CONFIG, {}):
        raise ConfigEntryNotReady('Configuration entry with username "%s" already set up' % (username,))

    # Source full configuration
    if config_entry.source == config_entries.SOURCE_IMPORT:
        # Source configuration from YAML
        yaml_config = hass.data.get(DATA_YAML_CONFIG)

        if not yaml_config or username not in yaml_config:
            _LOGGER.info('Removing entry %s after removal from YAML configuration.' % config_entry.entry_id)
            hass.async_create_task(
                hass.config_entries.async_remove(
                    config_entry.entry_id
                )
            )
            return False

        user_cfg = yaml_config[username]

    else:
        # Source and convert configuration from input data
        user_cfg = CONFIG_ENTRY_SCHEMA({**config_entry.data, **(config_entry.options or {})})

    _LOGGER.info('Setting up config entry for user "%s"' % username)

    from custom_components.mosenergosbyt.api import API, MosenergosbytException

    try:
        api_object = API(
            username=username,
            password=user_cfg[CONF_PASSWORD],
            user_agent=user_cfg.get(CONF_USER_AGENT)
        )

        await api_object.login()

        # Fetch all accounts
        accounts, unsupported_accounts = \
            await api_object.get_accounts(return_unsupported_accounts=True)

        # Filter accounts
        if CONF_FILTER in user_cfg:
            account_filter = user_cfg[CONF_FILTER]
            accounts = [account for account in accounts if account_filter[account.account_code]]

    except MosenergosbytException as e:
        _LOGGER.error('Error authenticating with user "%s": %s' % (username, str(e)))
        return False

    if unsupported_accounts:
        async_handle_unsupported_accounts(hass, username, unsupported_accounts)

    if not accounts:
        # Cancel setup because no accounts provided
        _LOGGER.warning('No supported accounts found under username "%s"', username)
        return False

    # Create data placeholders
    hass.data.setdefault(DATA_API_OBJECTS, {})[config_entry.entry_id] = api_object
    hass.data.setdefault(DATA_ENTITIES, {})[config_entry.entry_id] = {}
    hass.data.setdefault(DATA_UPDATERS, {})[config_entry.entry_id] = {}

    # Save final configuration data
    hass.data.setdefault(DATA_FINAL_CONFIG, {})[username] = user_cfg

    # Forward entry setup to sensor platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(
            config_entry,
            SENSOR_DOMAIN
        )
    )

    _LOGGER.debug('Successfully set up user "%s"' % username)
    return True


async def async_unload_entry(hass: HomeAssistantType, config_entry: config_entries.ConfigEntry):
    entry_id = config_entry.entry_id

    if DATA_API_OBJECTS in hass.data and entry_id in hass.data[DATA_API_OBJECTS]:
        # Remove API objects
        del hass.data[DATA_API_OBJECTS][entry_id]
        if not hass.data[DATA_API_OBJECTS]:
            del hass.data[DATA_API_OBJECTS]

    if DATA_ENTITIES in hass.data and entry_id in hass.data[DATA_ENTITIES]:
        # Remove references to created entities
        hass.async_create_task(
            hass.config_entries.async_forward_entry_unload(
                config_entry,
                SENSOR_DOMAIN
            )
        )

    username = config_entry.data[CONF_USERNAME]

    if DATA_FINAL_CONFIG in hass.data and username in hass.data[DATA_FINAL_CONFIG]:
        del hass.data[DATA_FINAL_CONFIG][entry_id]