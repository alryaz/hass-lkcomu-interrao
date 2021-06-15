__all__ = (
    "make_common_async_setup_entry",
    "MESEntity",
    "async_refresh_api_data",
    "async_register_update_delegator",
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
from homeassistant.const import ATTR_ATTRIBUTION, CONF_TYPE, CONF_USERNAME
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType, HomeAssistantType, StateType
from homeassistant.util import as_local, utcnow

from custom_components.lkcomu_interrao._util import _make_log_prefix
from custom_components.lkcomu_interrao.const import (
    ATTRIBUTION,
    DATA_API_OBJECTS,
    DATA_ENTITIES,
    DATA_FINAL_CONFIG,
    DATA_UPDATE_DELEGATORS,
    SUPPORTED_PLATFORMS,
)
from inter_rao_energosbyt.exceptions import EnergosbytException

if TYPE_CHECKING:
    from inter_rao_energosbyt.interfaces import Account, BaseEnergosbytAPI

_LOGGER = logging.getLogger(__name__)

_TMESEntity = TypeVar("_TMESEntity", bound="MESEntity")


def _get_key(config_entry: ConfigEntry) -> Tuple[str, str]:
    return config_entry.data[CONF_TYPE], config_entry.data[CONF_USERNAME]


AddEntitiesCallType = Callable[[List["MESEntity"], bool], Any]
UpdateDelegatorsDataType = Dict[str, Tuple[AddEntitiesCallType, Set[Type["MESEntity"]]]]


def make_common_async_setup_entry(entity_cls: Type["MESEntity"], *args: Type["MESEntity"]):
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
    entity_cls: Type["MESEntity"],
    *args: Type["MESEntity"],
    update_after_complete: bool = True,
):
    key = _get_key(config_entry)
    update_delegators: UpdateDelegatorsDataType = hass.data.setdefault(
        DATA_UPDATE_DELEGATORS, {}
    ).setdefault(key, {})
    update_delegators[platform] = (async_add_entities, {entity_cls, *args})

    if update_after_complete:
        if len(update_delegators) != len(SUPPORTED_PLATFORMS):
            return

        await async_refresh_api_data(hass, config_entry)


async def async_refresh_api_data(hass: HomeAssistantType, config_entry: ConfigEntry):
    key = _get_key(config_entry)
    api: "BaseEnergosbytAPI" = hass.data[DATA_API_OBJECTS][key]

    try:
        accounts = await api.async_update_accounts(with_related=False)
    except EnergosbytException:
        await api.async_authenticate()
        accounts = await api.async_update_accounts(with_related=False)

    update_delegators: Optional[UpdateDelegatorsDataType] = hass.data.get(
        DATA_UPDATE_DELEGATORS, {}
    ).get(key)

    if not update_delegators:
        return

    entities: Dict[Type["MESEntity"], Dict[Hashable, "MESEntity"]] = hass.data[
        DATA_ENTITIES
    ].setdefault(key, {})

    final_config = hass.data[DATA_FINAL_CONFIG][key]

    tasks = []

    async def _wrap_platform(async_add_entities_, platform_tasks_):
        all_new_entities_ = []
        for new_entities in await asyncio.gather(*platform_tasks_, return_exceptions=True):
            if not new_entities:
                continue

            if isinstance(new_entities, BaseException):
                _LOGGER.debug("Error ocurred: %s", new_entities)
                continue

            all_new_entities_.extend(new_entities)

        async_add_entities_(all_new_entities_, True)

    for platform, (async_add_entities, entity_classes) in update_delegators.items():
        platform_tasks = []
        for account_id, account in accounts.items():
            for entity_cls in entity_classes:
                current_entities = entities.setdefault(entity_cls, {})
                platform_tasks.append(
                    entity_cls.async_refresh_accounts(
                        current_entities,
                        account,
                        config_entry,
                        final_config,
                    )
                )

        if platform_tasks:
            tasks.append(_wrap_platform(async_add_entities, platform_tasks))

    if tasks:
        await asyncio.wait(map(hass.async_create_task, tasks))


class NameFormatDict(dict):
    def __missing__(self, key):
        return "{{" + str(key) + "}}"


_TData = TypeVar("_TData")
_TAccount = TypeVar("_TAccount", bound="Account")


class MESEntity(Entity, Generic[_TAccount, _TData]):
    config_key: ClassVar[str] = NotImplemented

    def __init__(
        self,
        name_format: str,
        scan_interval: timedelta,
        account: _TAccount,
        entity_data: Optional[_TData] = None,
    ) -> None:
        self._name_format = name_format
        self._scan_interval = scan_interval
        self._account: _TAccount = account

        self._entity_data: Optional[_TData] = entity_data
        self._entity_updater = None

    #################################################################################
    # Base overrides
    #################################################################################

    @property
    def entity_picture(self) -> str:
        return self._account.api.BASE_URL + "/favicon.ico"

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return False

    @property
    def device_state_attributes(self):
        """Return the attribute(s) of the sensor"""
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION % urlparse(self._account.api.BASE_URL).netloc,
            **(self.sensor_related_attributes or {}),
        }

    @property
    def name(self) -> Optional[str]:
        name_format_values = NameFormatDict(
            {
                key: ("" if value is None else value)
                for key, value in self.name_format_values.items()
            }
        )
        return self._name_format.format_map(name_format_values)

    #################################################################################
    # Hooks for adding entity to internal registry
    #################################################################################

    async def async_added_to_hass(self) -> None:
        _LOGGER.info(self.log_prefix + "Adding to HomeAssistant")

        self.updater_restart()

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.info(self.log_prefix + "Removing from HomeAssistant")
        self.updater_stop()

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
        self.updater_stop()

        async def _update_entity(*_):
            nonlocal self
            _LOGGER.debug(self.log_prefix + f"Executing updater on interval")
            await self.async_update_ha_state(force_refresh=True)

        _LOGGER.debug(
            self.log_prefix + f"Starting updater "
            f"(interval: {self._scan_interval.total_seconds()} seconds, "
            f"next call: {as_local(utcnow()) + self._scan_interval})"
        )
        self._entity_updater = async_track_time_interval(
            self.hass,
            _update_entity,
            self._scan_interval,
        )

    async def updater_execute(self) -> None:
        self.updater_stop()
        try:
            await self.async_update_ha_state(force_refresh=True)
        finally:
            self.updater_restart()

    #################################################################################
    # Functional base for inherent classes
    #################################################################################

    @classmethod
    @abstractmethod
    async def async_refresh_accounts(
        cls: Type[_TMESEntity],
        entities: Dict[Hashable, Optional[_TMESEntity]],
        account: "Account",
        config_entry: ConfigEntry,
        final_config: ConfigType,
    ) -> Optional[Iterable[_TMESEntity]]:
        raise NotImplementedError

    @abstractmethod
    async def async_update(self) -> None:
        raise NotImplementedError

    #################################################################################
    # Data-oriented base for inherent classes
    #################################################################################

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
