__all__ = (
    "make_common_async_setup_entry",
    "LkcomuEntity",
    "async_refresh_api_data",
    "async_register_update_delegator",
    "UpdateDelegatorsDataType",
    "EntitiesDataType",
)

import asyncio
import logging
from abc import abstractmethod
from datetime import timedelta
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    Hashable,
    Iterable,
    List,
    Mapping,
    Optional,
    Set,
    TYPE_CHECKING,
    Tuple,
    Type,
    TypeVar,
)
from urllib.parse import urlparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION, CONF_DEFAULT, CONF_SCAN_INTERVAL
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType, HomeAssistantType, StateType
from homeassistant.util import as_local, utcnow

from custom_components.lkcomu_interrao._util import (
    IS_IN_RUSSIA,
    _make_log_prefix,
    async_get_icons_for_providers,
)
from custom_components.lkcomu_interrao.const import (
    ATTRIBUTION_EN,
    ATTRIBUTION_RU,
    ATTR_ACCOUNT_CODE,
    ATTR_ACCOUNT_ID,
    CONF_ACCOUNTS,
    CONF_DEV_PRESENTATION,
    CONF_NAME_FORMAT,
    DATA_API_OBJECTS,
    DATA_ENTITIES,
    DATA_FINAL_CONFIG,
    DATA_PROVIDER_LOGOS,
    DATA_UPDATE_DELEGATORS,
    FORMAT_VAR_ACCOUNT_CODE,
    FORMAT_VAR_ACCOUNT_ID,
    FORMAT_VAR_CODE,
    FORMAT_VAR_PROVIDER_CODE,
    FORMAT_VAR_PROVIDER_NAME,
    SUPPORTED_PLATFORMS,
)
from inter_rao_energosbyt.enums import ProviderType
from inter_rao_energosbyt.exceptions import EnergosbytException

if TYPE_CHECKING:
    from homeassistant.helpers.entity_registry import RegistryEntry
    from inter_rao_energosbyt.interfaces import Account, BaseEnergosbytAPI

_LOGGER = logging.getLogger(__name__)

_TLkcomuEntity = TypeVar("_TLkcomuEntity", bound="LkcomuEntity")

AddEntitiesCallType = Callable[[List["MESEntity"], bool], Any]
UpdateDelegatorsDataType = Dict[str, Tuple[AddEntitiesCallType, Set[Type["MESEntity"]]]]
EntitiesDataType = Dict[Type["LkcomuEntity"], Dict[Hashable, "LkcomuEntity"]]


def make_common_async_setup_entry(entity_cls: Type["LkcomuEntity"], *args: Type["LkcomuEntity"]):
    async def _async_setup_entry(
        hass: HomeAssistantType,
        config_entry: ConfigEntry,
        async_add_devices,
    ):
        current_entity_platform = entity_platform.current_platform.get()
        log_prefix = _make_log_prefix(config_entry, current_entity_platform, "s")
        _LOGGER.debug(log_prefix + "Begin entry setup")

        await async_register_update_delegator(
            hass,
            config_entry,
            current_entity_platform.domain,
            async_add_devices,
            entity_cls,
            *args,
        )

        _LOGGER.debug(log_prefix + "End entry setup")

    _async_setup_entry.__name__ = "async_setup_entry"

    return _async_setup_entry


async def async_register_update_delegator(
    hass: HomeAssistantType,
    config_entry: ConfigEntry,
    platform: str,
    async_add_entities: AddEntitiesCallType,
    entity_cls: Type["LkcomuEntity"],
    *args: Type["LkcomuEntity"],
    update_after_complete: bool = True,
):
    entry_id = config_entry.entry_id

    update_delegators: UpdateDelegatorsDataType = hass.data[DATA_UPDATE_DELEGATORS][entry_id]
    update_delegators[platform] = (async_add_entities, {entity_cls, *args})

    if update_after_complete:
        if len(update_delegators) != len(SUPPORTED_PLATFORMS):
            return

        await async_refresh_api_data(hass, config_entry)


async def async_refresh_api_data(hass: HomeAssistantType, config_entry: ConfigEntry):
    entry_id = config_entry.entry_id
    api: "BaseEnergosbytAPI" = hass.data[DATA_API_OBJECTS][entry_id]

    try:
        accounts = await api.async_update_accounts(with_related=False)
    except EnergosbytException:
        await api.async_authenticate()
        accounts = await api.async_update_accounts(with_related=False)

    update_delegators: UpdateDelegatorsDataType = hass.data[DATA_UPDATE_DELEGATORS][entry_id]

    if not update_delegators:
        return

    try:
        provider_icons = await async_get_icons_for_providers(
            api, set(map(lambda x: x.provider_type, accounts.values()))
        )
    except BaseException as e:
        _LOGGER.warning(
            entry_id
            + (
                "Произошла ошибка при обновлении логотипов"
                if IS_IN_RUSSIA
                else "Error occurred while updating logos"
            )
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
    final_config: ConfigType = hass.data[DATA_FINAL_CONFIG][entry_id]

    dev_presentation = final_config.get(CONF_DEV_PRESENTATION)
    dev_classes_processed = set()

    platform_tasks = {}

    accounts_config = final_config.get(CONF_ACCOUNTS) or {}
    account_default_config = final_config[CONF_DEFAULT]

    for account_id, account in accounts.items():
        account_config = accounts_config.get(account.code)

        if account_config is None:
            account_config = account_default_config

        if account_config is False:
            continue

        for platform, (_, entity_classes) in update_delegators.items():
            add_update_tasks = platform_tasks.setdefault(platform, [])
            for entity_cls in entity_classes:
                if account_config[entity_cls.config_key] is False:
                    continue

                if dev_presentation:
                    if (entity_cls, account.provider_type) in dev_classes_processed:
                        continue
                    dev_classes_processed.add((entity_cls, account.provider_type))

                current_entities = entities.setdefault(entity_cls, {})

                add_update_tasks.append(
                    entity_cls.async_refresh_accounts(
                        current_entities,
                        account,
                        config_entry,
                        account_config,
                    )
                )

    if platform_tasks:
        for platform, tasks in zip(
            platform_tasks.keys(),
            await asyncio.gather(
                *map(lambda x: asyncio.gather(*x, return_exceptions=True), platform_tasks.values())
            ),
        ):
            all_new_entities = []
            for results in tasks:
                if results is None:
                    continue
                if isinstance(results, BaseException):
                    _LOGGER.error(f"Error occurred: {repr(results)}")
                    continue
                all_new_entities.extend(results)

            if all_new_entities:
                update_delegators[platform][0](all_new_entities, True)


class NameFormatDict(dict):
    def __missing__(self, key: str):
        if key.endswith("_upper") and key[:-6] in self:
            return str(self[key[:-6]]).upper()
        if key.endswith("_cap") and key[:-4] in self:
            return str(self[key[:-4]]).capitalize()
        if key.endswith("_title") and key[:-6] in self:
            return str(self[key[:-6]]).title()
        return "{{" + str(key) + "}}"


_TData = TypeVar("_TData")
_TAccount = TypeVar("_TAccount", bound="Account")


class LkcomuEntity(Entity, Generic[_TAccount]):
    config_key: ClassVar[str] = NotImplemented

    def __init__(
        self,
        account: _TAccount,
        account_config: ConfigType,
    ) -> None:
        self._account: _TAccount = account
        self._account_config: ConfigType = account_config
        self._entity_updater = None

    #################################################################################
    # Config getter helpers
    #################################################################################

    @property
    def account_provider_code(self) -> Optional[str]:
        try:
            return ProviderType(self._account.provider_type).name.lower()
        except (ValueError, TypeError):
            return None

    @property
    def scan_interval(self) -> timedelta:
        return self._account_config[CONF_SCAN_INTERVAL][self.config_key]

    @property
    def name_format(self) -> str:
        return self._account_config[CONF_NAME_FORMAT][self.config_key]

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
    def device_state_attributes(self):
        """Return the attribute(s) of the sensor"""
        attribution = (ATTRIBUTION_RU if IS_IN_RUSSIA else ATTRIBUTION_EN) % urlparse(
            self._account.api.BASE_URL
        ).netloc

        return {
            ATTR_ATTRIBUTION: attribution,
            **(self.sensor_related_attributes or {}),
            ATTR_ACCOUNT_ID: self._account.id,
            ATTR_ACCOUNT_CODE: self._account.code,
        }

    @property
    def name(self) -> Optional[str]:
        name_format_values = NameFormatDict(
            {
                key: ("" if value is None else value)
                for key, value in self.name_format_values.items()
            }
        )

        if FORMAT_VAR_CODE not in name_format_values:
            name_format_values[FORMAT_VAR_CODE] = self.code

        if FORMAT_VAR_ACCOUNT_CODE not in name_format_values:
            name_format_values[FORMAT_VAR_ACCOUNT_CODE] = self._account.code

        if FORMAT_VAR_ACCOUNT_ID not in name_format_values:
            name_format_values[FORMAT_VAR_ACCOUNT_ID] = str(self._account.id)

        if FORMAT_VAR_PROVIDER_CODE not in name_format_values:
            name_format_values[FORMAT_VAR_PROVIDER_CODE] = self.account_provider_code or "unknown"

        if FORMAT_VAR_PROVIDER_NAME not in name_format_values:
            name_format_values[FORMAT_VAR_PROVIDER_NAME] = self._account.provider_name

        return self.name_format.format_map(name_format_values)

    #################################################################################
    # Hooks for adding entity to internal registry
    #################################################################################

    async def async_added_to_hass(self) -> None:
        _LOGGER.info(self.log_prefix + "Adding to HomeAssistant")

        self.updater_restart()

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.info(self.log_prefix + "Removing from HomeAssistant")
        self.updater_stop()

        registry_entry: Optional["RegistryEntry"] = self.registry_entry
        if registry_entry:
            entry_id: Optional[str] = registry_entry.config_entry_id
            if entry_id:
                data_entities: EntitiesDataType = self.hass.data[DATA_ENTITIES][entry_id]
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
        try:
            await self.async_update_internal()
        except EnergosbytException:
            # @TODO: more sophisticated error handling
            await self._account.api.async_authenticate()
            await self.async_update_internal()

    #################################################################################
    # Functional base for inherent classes
    #################################################################################

    @classmethod
    @abstractmethod
    async def async_refresh_accounts(
        cls: Type[_TLkcomuEntity],
        entities: Dict[Hashable, _TLkcomuEntity],
        account: "Account",
        config_entry: ConfigEntry,
        account_config: ConfigType,
    ) -> Optional[Iterable[_TLkcomuEntity]]:
        raise NotImplementedError

    #################################################################################
    # Data-oriented base for inherent classes
    #################################################################################

    @abstractmethod
    async def async_update_internal(self) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def code(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def state(self) -> StateType:
        raise NotImplementedError

    @property
    @abstractmethod
    def icon(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def sensor_related_attributes(self) -> Optional[Mapping[str, Any]]:
        raise NotImplementedError

    @property
    @abstractmethod
    def name_format_values(self) -> Mapping[str, Any]:
        raise NotImplementedError

    @property
    @abstractmethod
    def unique_id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def device_class(self) -> Optional[str]:
        raise NotImplementedError
