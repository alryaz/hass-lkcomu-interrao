import asyncio
import datetime
import re
from datetime import timedelta
from typing import Any, Dict, Optional, Set, TYPE_CHECKING, Type, Union

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.helpers.typing import HomeAssistantType

from custom_components.lkcomu_interrao.const import DOMAIN
from inter_rao_energosbyt.enums import ProviderType

if TYPE_CHECKING:
    from inter_rao_energosbyt.interfaces import BaseEnergosbytAPI


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


RE_FAVICON = re.compile(r'["\']?REACT_APP_FAVICON["\']?\s*:\s*"([\w\.]+\.ico)"')


def _code_search_index(code: str):
    return


ICONS_FOR_PROVIDERS: Dict[str, Optional[Union[asyncio.Future, str]]] = {}


async def async_get_icons_for_providers(
    api: "BaseEnergosbytAPI", provider_types: Set[int]
) -> Dict[str, str]:
    session = api._session
    base_url = api.BASE_URL
    icons = {}

    async with session.get(base_url + "/asset-manifest.json") as response:
        manifest = await response.json()

    iter_types = []

    for provider_type in provider_types:
        try:
            code = ProviderType(provider_type).name.lower()
        except (ValueError, TypeError):
            continue
        else:
            iter_types.append(code)

    for code in iter_types:
        search_index = tuple(map(str.lower, (code + "Logo", "defaultMarker" + code)))
        for key in manifest:
            lower_key = key.lower()
            for index_key in search_index:
                if index_key in lower_key:
                    icons[code] = base_url + "/" + manifest[key]
                    break

            if (
                code not in icons
                and code in key
                and (
                    lower_key.endswith(".png")
                    or lower_key.endswith(".jpg")
                    or lower_key.endswith(".svg")
                )
            ):
                icons[code] = base_url + "/" + manifest[key]

    if "main.js" in manifest:
        async with session.get(base_url + "/" + manifest["main.js"]) as response:
            js_code = await response.text()

        m = RE_FAVICON.search(js_code)
        if m:
            url = base_url + "/" + m.group(1)
            for code in iter_types:
                icons.setdefault(code, url)

    return icons


async def async_update_provider_icons(api: "BaseEnergosbytAPI") -> Optional[str]:
    if code in ICONS_FOR_PROVIDERS:
        current_code = ICONS_FOR_PROVIDERS[code]
        if isinstance(current_code, asyncio.Future):
            return await current_code
        return current_code

    code_future = asyncio.get_event_loop().create_future()
    ICONS_FOR_PROVIDERS[code] = code_future

    try:
        result = await async_get_icons_for_providers(api, code)
    except BaseException as e:
        code_future.set_exception(e)
        del ICONS_FOR_PROVIDERS[code]
        raise
    else:
        code_future.set_result(result)
        ICONS_FOR_PROVIDERS[code] = result

    return result


LOCAL_TIMEZONE = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo

# Kaliningrad is excluded as it is not supported
IS_IN_RUSSIA = timedelta(hours=3) <= LOCAL_TIMEZONE.utcoffset(None) <= timedelta(hours=12)
