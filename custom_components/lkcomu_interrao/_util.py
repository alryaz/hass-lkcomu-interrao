from typing import Any, Optional, Type, Union

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.helpers.typing import HomeAssistantType

from custom_components.lkcomu_interrao.const import DOMAIN


def _make_log_prefix(
    config_entry: Union[Any, ConfigEntry], domain: Union[Any, EntityPlatform], *args
):
    join_args = [
        (
            config_entry.entry_id[-6:]
            if isinstance(config_entry, ConfigEntry)
            else str(config_entry)
        ),
        (domain.domain if isinstance(domain, EntityPlatform) else str(domain)),
    ]
    if args:
        join_args.extend(map(str, args))

    return "[" + "][".join(join_args) + "] "


@callback
def _find_existing_entry(
    hass: HomeAssistantType, type_: str, username: str
) -> Optional[config_entries.ConfigEntry]:
    existing_entries = hass.config_entries.async_entries(DOMAIN)
    for config_entry in existing_entries:
        if config_entry.data[CONF_TYPE] == type_ and config_entry.data[CONF_USERNAME] == username:
            return config_entry


def import_api_cls(type_: str) -> Type["BaseEnergosbytAPI"]:
    return __import__("inter_rao_energosbyt.api." + type_, globals(), locals(), ("API",)).API
