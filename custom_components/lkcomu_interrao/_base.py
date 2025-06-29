__all__ = (
    "make_common_async_setup_entry",
    "LkcomuInterRAOEntity",
    "async_refresh_api_data",
    "async_register_update_delegator",
    "UpdateDelegatorsDataType",
    "EntitiesDataType",
    "SupportedServicesType",
)

import asyncio
import logging
from abc import abstractmethod
from datetime import timedelta
from typing import (
    Any,
    Callable,
    ClassVar,
    Generic,
    Hashable,
    Iterable,
    Mapping,
    SupportsInt,
    TYPE_CHECKING,
    TypeVar,
    Union,
)
from urllib.parse import urlparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_DEFAULT,
    CONF_SCAN_INTERVAL,
    CONF_TYPE,
    CONF_USERNAME,
)
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.core import HomeAssistant
from homeassistant.util import as_local, utcnow

from custom_components.lkcomu_interrao._util import (
    async_get_icons_for_providers,
    mask_username,
    with_auto_auth,
)
from custom_components.lkcomu_interrao.const import (
    ATTRIBUTION,
    ATTR_ACCOUNT_CODE,
    ATTR_ACCOUNT_ID,
    CONF_ACCOUNTS,
    DATA_API_OBJECTS,
    DATA_ENTITIES,
    DATA_FINAL_CONFIG,
    DATA_PROVIDER_LOGOS,
    DATA_UPDATE_DELEGATORS,
    DOMAIN,
    SUPPORTED_PLATFORMS,
)
from inter_rao_energosbyt.enums import ProviderType

if TYPE_CHECKING:
    from homeassistant.helpers.entity_registry import RegistryEntry
    from inter_rao_energosbyt.interfaces import Account, BaseEnergosbytAPI

_LOGGER = logging.getLogger(__name__)

_TLkcomuInterRAOEntity = TypeVar("_TLkcomuInterRAOEntity", bound="LkcomuInterRAOEntity")

AddEntitiesCallType = Callable[[list["MESEntity"], bool], Any]
UpdateDelegatorsDataType = dict[str, tuple[AddEntitiesCallType, set[type["MESEntity"]]]]
EntitiesDataType = dict[
    type["LkcomuInterRAOEntity"], dict[Hashable, "LkcomuInterRAOEntity"]
]


def make_common_async_setup_entry(
    entity_cls: type["LkcomuInterRAOEntity"], *args: type["LkcomuInterRAOEntity"]
):
    async def _async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_devices,
    ):
        current_entity_platform = entity_platform.current_platform.get()

        log_prefix = (
            f"[{config_entry.data[CONF_TYPE]}/{mask_username(config_entry.data[CONF_USERNAME])}]"
            f"[{current_entity_platform.domain}][setup] "
        )
        _LOGGER.debug(log_prefix + "Registering update delegator")

        await async_register_update_delegator(
            hass,
            config_entry,
            current_entity_platform.domain,
            async_add_devices,
            entity_cls,
            *args,
        )

    _async_setup_entry.__name__ = "async_setup_entry"

    return _async_setup_entry


async def async_register_update_delegator(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    platform: str,
    async_add_entities: AddEntitiesCallType,
    entity_cls: type["LkcomuInterRAOEntity"],
    *args: type["LkcomuInterRAOEntity"],
    update_after_complete: bool = True,
):
    entry_id = config_entry.entry_id

    update_delegators: UpdateDelegatorsDataType = hass.data[DATA_UPDATE_DELEGATORS][
        entry_id
    ]
    update_delegators[platform] = (async_add_entities, {entity_cls, *args})

    if update_after_complete:
        if len(update_delegators) != len(SUPPORTED_PLATFORMS):
            return

        await async_refresh_api_data(hass, config_entry)


async def async_refresh_api_data(hass: HomeAssistant, config_entry: ConfigEntry):
    entry_id = config_entry.entry_id
    api: "BaseEnergosbytAPI" = hass.data[DATA_API_OBJECTS][entry_id]

    accounts = await with_auto_auth(api, api.async_update_accounts, with_related=False)

    update_delegators: UpdateDelegatorsDataType = hass.data[DATA_UPDATE_DELEGATORS][
        entry_id
    ]

    log_prefix_base = f"[{config_entry.data[CONF_TYPE]}/{mask_username(config_entry.data[CONF_USERNAME])}]"
    refresh_log_prefix = log_prefix_base + "[refresh] "

    _LOGGER.info(refresh_log_prefix + "Beginning profile-related data update")

    if not update_delegators:
        return

    try:
        provider_icons = await async_get_icons_for_providers(
            api, set(map(lambda x: x.provider_type, accounts.values()))
        )
    except BaseException as e:
        _LOGGER.warning(
            log_prefix_base
            + "[logos] "
            + "Error occurred while updating logos"
            + ": "
            + repr(e)
        )
    else:
        if provider_icons:
            if DATA_PROVIDER_LOGOS in hass.data:
                hass.data[DATA_PROVIDER_LOGOS].update(provider_icons)
            else:
                hass.data[DATA_PROVIDER_LOGOS] = provider_icons

    entities: EntitiesDataType = hass.data[DATA_ENTITIES][entry_id]
    final_config: ConfigType = dict(hass.data[DATA_FINAL_CONFIG][entry_id])

    platform_tasks = {}

    accounts_config = final_config.get(CONF_ACCOUNTS) or {}
    account_default_config = final_config[CONF_DEFAULT]

    for account_id, account in accounts.items():
        account_config = accounts_config.get(account.code)
        account_log_prefix_base = (
            refresh_log_prefix + f"[{mask_username(account.code)}]"
        )

        if account_config is None:
            account_config = account_default_config

        if account_config is False:
            continue

        for platform, (_, entity_classes) in update_delegators.items():
            platform_log_prefix_base = account_log_prefix_base + f"[{platform}]"
            add_update_tasks = platform_tasks.setdefault(platform, [])
            for entity_cls in entity_classes:
                cls_log_prefix_base = (
                    platform_log_prefix_base + f"[{entity_cls.__name__}]"
                )
                if account_config[entity_cls.config_key] is False:
                    _LOGGER.debug(
                        log_prefix_base + " " + "Account skipped due to filtering"
                    )
                    continue

                current_entities = entities.setdefault(entity_cls, {})

                _LOGGER.debug(
                    cls_log_prefix_base + "[update] " + "Planning update procedure"
                )

                add_update_tasks.append(
                    entity_cls.async_refresh_accounts(
                        current_entities,
                        account,
                        config_entry,
                        account_config,
                    )
                )

    if platform_tasks:

        async def _wrap_update_task(update_task):
            try:
                return await update_task
            except BaseException as task_exception:
                _LOGGER.exception(
                    f"Error occurred during task execution: {repr(task_exception)}",
                    exc_info=task_exception,
                )
                return None

        all_updates_count = sum(map(len, platform_tasks.values()))
        _LOGGER.info(
            refresh_log_prefix
            + (
                f"Performing update procedures ({all_updates_count}) for platforms: "
                f"{', '.join(platform_tasks.keys())}"
            )
        )
        for platform, tasks in zip(
            platform_tasks.keys(),
            await asyncio.gather(
                *map(
                    lambda x: asyncio.gather(*map(_wrap_update_task, x)),
                    platform_tasks.values(),
                )
            ),
        ):
            all_new_entities = []
            for results in tasks:
                if results is None:
                    continue
                all_new_entities.extend(results)

            if all_new_entities:
                update_delegators[platform][0](all_new_entities, True)
    else:
        _LOGGER.warning(
            refresh_log_prefix + "Missing suitable platforms for configuration"
        )


_TData = TypeVar("_TData")
_TAccount = TypeVar("_TAccount", bound="Account")


SupportedServicesType = Mapping[
    tuple[type, SupportsInt] | None,
    Mapping[str, Union[dict, Callable[[dict], dict]]],
]


class LkcomuInterRAOEntity(Entity, Generic[_TAccount]):
    config_key: ClassVar[str] = NotImplemented

    _supported_services: ClassVar[SupportedServicesType] = {}

    def __init__(
        self,
        account: _TAccount,
        account_config: ConfigType,
    ) -> None:
        self._account: _TAccount = account
        self._account_config: ConfigType = account_config
        self._entity_updater = None

    @property
    def api_hostname(self) -> str:
        return urlparse(self._account.api.BASE_URL).netloc

    @property
    def device_info(self) -> dict[str, Any]:
        account_object = self._account

        device_info = {
            "name": f"№ {account_object.code}",
            "identifiers": {
                (DOMAIN, f"{account_object.__class__.__name__}__{account_object.id}")
            },
            "manufacturer": account_object.provider_name,
            "model": self.api_hostname,
            "sw_version": account_object.api.APP_VERSION,  # placeholder for future releases
        }

        # account_address = account_object.address
        # if account_address is not None:
        #     device_info["suggested_area"] = account_address

        return device_info

    #################################################################################
    # Config getter helpers
    #################################################################################

    @property
    def account_provider_code(self) -> str | None:
        try:
            return ProviderType(self._account.provider_type).name.lower()
        except (ValueError, TypeError):
            return None

    @property
    def scan_interval(self) -> timedelta:
        return self._account_config[CONF_SCAN_INTERVAL][self.config_key]

    #################################################################################
    # Base overrides
    #################################################################################

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return False

    @property
    def extra_state_attributes(self):
        """Return the attribute(s) of the sensor"""

        attributes = {
            ATTR_ATTRIBUTION: (ATTRIBUTION) % self.api_hostname,
            **(self.sensor_related_attributes or {}),
        }

        if ATTR_ACCOUNT_ID not in attributes:
            attributes[ATTR_ACCOUNT_ID] = self._account.id

        if ATTR_ACCOUNT_CODE not in attributes:
            attributes[ATTR_ACCOUNT_CODE] = self._account.code

        return attributes

    #################################################################################
    # Hooks for adding entity to internal registry
    #################################################################################

    async def async_added_to_hass(self) -> None:
        _LOGGER.info(self.log_prefix + "Adding to HomeAssistant")
        self.updater_restart()

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.info(self.log_prefix + "Removing from HomeAssistant")
        self.updater_stop()

        registry_entry = self.registry_entry
        if registry_entry:
            entry_id = registry_entry.config_entry_id
            if entry_id:
                data_entities: EntitiesDataType = self.hass.data[DATA_ENTITIES][
                    entry_id
                ]
                cls_entities = data_entities.get(self.__class__)
                if cls_entities:
                    remove_indices = []
                    for idx, entity in enumerate(cls_entities):
                        if self is entity:
                            remove_indices.append(idx)
                    for idx in remove_indices:
                        cls_entities.pop(idx)

    #################################################################################
    # Updater management API
    #################################################################################

    @property
    def log_prefix(self) -> str:
        return f"[{self.config_key}][{self.entity_id or '<no entity ID>'}] "

    def updater_stop(self) -> None:
        if self._entity_updater is not None:
            _LOGGER.debug(self.log_prefix + "Stopping updater")
            self._entity_updater()
            self._entity_updater = None

    def updater_restart(self) -> None:
        log_prefix = self.log_prefix
        scan_interval = self.scan_interval

        self.updater_stop()

        async def _update_entity(*_):
            nonlocal self
            _LOGGER.debug(log_prefix + f"Executing updater on interval")
            await self.async_update_ha_state(force_refresh=True)

        _LOGGER.debug(
            log_prefix + f"Starting updater "
            f"(interval: {scan_interval.total_seconds()} seconds, "
            f"next call: {as_local(utcnow()) + scan_interval})"
        )
        self._entity_updater = async_track_time_interval(
            self.hass,
            _update_entity,
            scan_interval,
        )

    async def updater_execute(self) -> None:
        self.updater_stop()
        try:
            await self.async_update_ha_state(force_refresh=True)
        finally:
            self.updater_restart()

    async def async_update(self) -> None:
        # @TODO: more sophisticated error handling
        await with_auto_auth(self._account.api, self.async_update_internal)

    #################################################################################
    # Functional base for inherent classes
    #################################################################################

    @classmethod
    @abstractmethod
    async def async_refresh_accounts(
        cls: type[_TLkcomuInterRAOEntity],
        entities: dict[Hashable, _TLkcomuInterRAOEntity],
        account: "Account",
        config_entry: ConfigEntry,
        account_config: ConfigType,
    ) -> Iterable[_TLkcomuInterRAOEntity] | None:
        raise NotImplementedError

    #################################################################################
    # Data-oriented base for inherent classes
    #################################################################################

    @abstractmethod
    async def async_update_internal(self) -> None:
        raise NotImplementedError

    @property
    def code(self) -> str:
        return self._account.code

    @property
    @abstractmethod
    def sensor_related_attributes(self) -> Mapping[str, Any] | None:
        raise NotImplementedError

    @property
    @abstractmethod
    def unique_id(self) -> str:
        raise NotImplementedError

    def register_supported_services(self, for_object: Any | None = None) -> None:
        for type_feature, services in self._supported_services.items():
            result, features = (
                (True, None)
                if type_feature is None
                else (isinstance(for_object, type_feature[0]), (int(type_feature[1]),))
            )

            if result:
                for service, schema in services.items():
                    self.platform.async_register_entity_service(
                        service, schema, "async_service_" + service, features
                    )
