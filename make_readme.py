import html
import json
import re
from genericpath import exists
from io import StringIO
from os import getcwd, listdir, makedirs, path, rename
from typing import TextIO

from homeassistant.const import ATTR_SERVICE, CONF_DEFAULT, CONF_PASSWORD, CONF_TYPE, CONF_USERNAME
from itertools import chain
from sys import stdout
from time import sleep

from custom_components.lkcomu_interrao import (
    API_TYPE_DEFAULT,
    API_TYPE_NAMES,
    CONF_ACCOUNTS,
    CONF_LAST_INVOICE,
    DOMAIN,
    import_api_cls,
)
from custom_components.lkcomu_interrao._schema import CONFIG_ENTRY_SCHEMA
from custom_components.lkcomu_interrao.const import (
    ATTR_ACCOUNT_CODE,
    ATTR_ACCOUNT_ID,
    ATTR_AGENT,
    ATTR_AMOUNT,
    ATTR_BENEFITS,
    ATTR_CHARGED,
    ATTR_DESCRIPTION,
    ATTR_END,
    ATTR_GROUP,
    ATTR_INITIAL,
    ATTR_INSURANCE,
    ATTR_INVOICE_ID,
    ATTR_PAID,
    ATTR_PAID_AT,
    ATTR_PENALTY,
    ATTR_PERIOD,
    ATTR_PREVIOUS,
    ATTR_START,
    ATTR_STATUS,
    ATTR_SUCCESS,
    ATTR_SUM,
    ATTR_TOTAL,
    CONF_LAST_PAYMENT,
    CONF_LOGOS,
    CONF_METERS,
)
from custom_components.lkcomu_interrao.sensor import (
    SERVICE_CALCULATE_INDICATIONS,
    SERVICE_GET_INVOICES,
    SERVICE_GET_PAYMENTS,
    SERVICE_PUSH_INDICATIONS,
    SERVICE_SET_DESCRIPTION,
)
from inter_rao_energosbyt.enums import ProviderType, ServiceType
from inter_rao_energosbyt.interfaces import (
    AbstractAccountWithInvoices,
    AbstractAccountWithMeters,
    AbstractAccountWithPayments,
)


def move_next_saved_image(images_path: str, code: str, save_image_type: str):
    output_dir = path.join(images_path, code)
    new_image_path = path.join(output_dir, save_image_type + ".png")
    if exists(new_image_path):
        return
    found_file = None
    try:
        print(f"Image for {code} - {save_image_type}: ", end="")
        stdout.flush()
        while True:
            files = listdir(images_path)
            for file in files:
                if file.endswith(".png"):
                    print(file)
                    stdout.flush()
                    found_file = path.join(images_path, file)
                    break

            if found_file:
                break

            sleep(0.25)
    except KeyboardInterrupt:
        print("<skipped>")
        stdout.flush()
        sleep(0.25)
        return

    makedirs(output_dir, exist_ok=True)
    rename(found_file, new_image_path)


ACCOUNT_ENT_TYPE = ("Информация о лицевом счёте", CONF_ACCOUNTS)

SUPPORT_TYPES = {
    AbstractAccountWithMeters: ("Счётчик коммунальных услуг", CONF_METERS),
    AbstractAccountWithPayments: ("Последний зарегистрированный платёж", CONF_LAST_PAYMENT),
    AbstractAccountWithInvoices: ("Последняя выпущенная квитанция", CONF_LAST_INVOICE),
}


def routine_collect_images(images_root_path: str):
    providers_path = path.join(images_root_path, "providers")
    for provider_type in list(ProviderType):
        provider_type_code = provider_type.name.lower()
        for stuff_type in SUPPORT_TYPES.keys():
            move_next_saved_image(providers_path, provider_type_code, stuff_type)


RAW_ROOT_URL = "https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main"
RAW_IMAGES_URL = RAW_ROOT_URL + "/images"
RAW_HEADERS_URL = RAW_IMAGES_URL + "/headers"

ROOT = getcwd()
ROOT_IMAGES = path.join(ROOT, "images")
ROOT_HEADERS = path.join(ROOT_IMAGES, "headers")

SERVICE_TYPE_NAMES = {
    ServiceType.EPD: "ЕПД",
    ServiceType.ELECTRICITY: "Электричество",
    ServiceType.TRASH: "ТКО",
    ServiceType.HEATING: "Отопление",
}


def _write_by_code(output: TextIO, type_: str):
    api_cls = import_api_cls(type_)
    output.write(f"### {API_TYPE_NAMES[type_]} - `{type_}`\n")
    link_content = f'Ссылка на личный кабинет "{API_TYPE_NAMES[type_]}"'
    header_path = path.join(ROOT_HEADERS, type_ + ".png")
    if path.exists(header_path):
        link_content = f"![{html.escape(link_content)}]({RAW_HEADERS_URL}/{type_}.png)"

    output.write(f"[{link_content}]({api_cls.BASE_URL})\n")
    output.write("\n")

    output.write(
        f"#### Пример конфигурации:\n\n"
        f"```yaml\n"
        f"...\n"
        f"lkcomu_interrao:\n"
        f"  type: {type_}\n"
        f"  username: username1\n"
        f"  password: password1\n"
        f"```\n\n"
    )

    for (provider_type_id, service_type), account_cls in api_cls.SUPPORTED_ACCOUNTS.items():
        if provider_type_id is None:
            continue
        provider_type = ProviderType(provider_type_id)

        output.write(
            f"#### Поставщик `{provider_type.name}`"
            f" &mdash; "
            f"{SERVICE_TYPE_NAMES[service_type] if service_type else 'generic'}"
            f"\n"
        )

        supported_stuffs = []

        for condition in SUPPORT_TYPES.keys():
            if isinstance(condition, type):
                condition_result = issubclass(account_cls, condition)
            else:
                condition_result = condition(account_cls)

            if condition_result:
                supported_stuffs.append(condition)

        output.write("Для поставщика реализована поддержка следующих объектов:\n")
        for comment, screenshot_key in sorted(
            chain((ACCOUNT_ENT_TYPE,), map(SUPPORT_TYPES.__getitem__, supported_stuffs)),
            key=lambda x: x[0],
        ):
            summary_content = "Снимок экрана не предусмотрен"
            if screenshot_key:
                summary_content = "Снимок экрана отсутствует"
                stuff_image = path.join(
                    ROOT_IMAGES,
                    "providers",
                    provider_type.name.lower(),
                    screenshot_key + ".png",
                )
                if path.exists(stuff_image):
                    summary_content = f'<img src="{RAW_IMAGES_URL}/providers/{provider_type.name.lower()}/{screenshot_key}.png" alt="Скриншот">'

            output.write(
                f"<details>\n  <summary>{html.escape(comment)}</summary> \n  {summary_content}\n</details>\n"
            )

        output.write("\n")


def _get_providers_content() -> str:
    output = StringIO()

    output.write("## Поддерживаемые ЛК\n\n")

    output.write(
        """Ниже предъявлен перечень поддерживаемых ЛК с их внутренними идентификаторами.
Данные идентификаторы используются как значение для поля `type`.

> **Внимание:** Поддерживаются только ЛК физических лиц. Поддержка ЛК юридических лиц не планируется.
"""
    )

    from inter_rao_energosbyt.api import __all__ as api_types

    for api_type in sorted(
        api_types, key=lambda x: (len(import_api_cls(x).SUPPORTED_ACCOUNTS), x), reverse=True
    ):
        _write_by_code(output, api_type)

    return output.getvalue()


def _get_gui_configuration() -> str:
    with open("custom_components/lkcomu_interrao/translations/ru.json", "r", encoding="utf-8") as f:
        trans_ru = json.load(f)

    with open("custom_components/lkcomu_interrao/translations/en.json", "r", encoding="utf-8") as f:
        trans_en = json.load(f)

    return (
        "### Через раздел интеграции\n"
        '1. Перейдите в подраздел _"[Интеграции](https://my.home-assistant.io/redirect/integrations)"_ в разделе _"Настройки"_\n'
        '2. Нажмите кнопку _"Добавить интеграцию"_\n'
        f"3. Введите в поисковую строку: **_{trans_ru['title']}_** (англ. **_{trans_en['title']}_**)\n"
        f"4. Выберите найденную интеграцию\n"
        f"5. Следуйте инструкциям мастера по добавлению\n"
        f"\n"
        f"_Примечание:_ Поле **_{trans_ru['config']['step']['user']['data']['user_agent']}_** (англ. **_{trans_en['config']['step']['user']['data']['user_agent']}_**) генерируется автоматически.\n"
    )


_ONLY_SUPPORTED_OBJECTS_WARNING = "> Только для объектов, поддерживающих данный функционал"
_HEADER_PARAMETERS = "###### Параметры"
_HEADER_RESULTS = "###### Результат"


def _service_header(service_id: str, title: str, is_supported_only: bool = False):
    result = f"##### `{service_id}` &mdash; {title}\n\n"

    if is_supported_only:
        result += f"{_ONLY_SUPPORTED_OBJECTS_WARNING}\n\n"

    return result


def _simple_dated_request(service_id: str, title: str):
    return (
        _service_header(service_id, title, True) + f"\n"
        f"{_HEADER_PARAMETERS}\n"
        f"\n"
        f"- `{ATTR_START}: str | None` - _(опционально)_ Дата начала периода\n"
        f"- `{ATTR_END}: str | None` - _(опционально)_ Дата окончания периода\n"
        f"\n"
        f"{_HEADER_RESULTS}\n"
        f"\n"
        f"Событие с идентификатором `{DOMAIN}_{service_id}` и следующими значениями:\n"
    )


def _get_service_get_payments() -> str:
    return (
        f"{_simple_dated_request(SERVICE_GET_PAYMENTS, 'Получение платежей по периодам')}\n"
        f"- `{ATTR_SUM}: float` - сумма всех платежей за указанный период\n"
        f"- `{ATTR_AMOUNT}: float` - объём платежа\n"
        f"- `{ATTR_PAID_AT}: str` - дата/время платежа\n"
        f"- `{ATTR_PERIOD}: str` - период, за который платёж был выполнен\n"
        f"- `{ATTR_STATUS}: str | None` - состояние платежа\n"
        f"- `{ATTR_AGENT}: str | None` - банк-обработчик платежа\n"
        f"- `{ATTR_GROUP}: str | None` - группа платежа (для лицевых счетов с несколькими типами платежей)\n"
        f"\n"
    )


def _get_service_get_invoices() -> str:
    return (
        f"{_simple_dated_request(SERVICE_GET_INVOICES, 'Получение квитанций по периодам')}\n"
        f"- `{ATTR_SUM}: float` - сумма всех квитанций за указанный период\n"
        f"- `{ATTR_PERIOD}: str` - период квитанции\n"
        f"- `{ATTR_INVOICE_ID}: str` - идентификатор квитанции\n"
        f"- `{ATTR_TOTAL}: float` - сумма к оплате по квитанции\n"
        f"- `{ATTR_PAID}: float | None` - сумма оплат, учтённых к квитанции\n"
        f"- `{ATTR_INITIAL}: float | None` - задолженность/избыток на начало периода\n"
        f"- `{ATTR_CHARGED}: float | None` - начислено за период\n"
        f"- `{ATTR_INSURANCE}: float | None` - добровольное страхование\n"
        f"- `{ATTR_BENEFITS}: float | None` - льготы\n"
        f"- `{ATTR_PENALTY}: float | None` - штрафы\n"
        f"- `{ATTR_SERVICE}: float | None` - тех. обслуживание\n"
    )


def _get_service_push_indications() -> str:
    return _service_header(SERVICE_PUSH_INDICATIONS, "Передача показаний", True)


def _get_service_calculate_indications() -> str:
    return _service_header(SERVICE_CALCULATE_INDICATIONS, "Подсчёт показаний", True)


def _get_service_set_description() -> str:
    return (
        _service_header(SERVICE_SET_DESCRIPTION, "Установить описание лицевого счёта")
        + f"Устанавливает описание для лицевого счёта и провоцирует его обновление.\n"
        f"\n"
        f"{_HEADER_PARAMETERS}\n"
        f"\n"
        f"- `{ATTR_DESCRIPTION}: str | None` - _(опционально)_ Новое описание для лицевого счёта\n"
        f"\n"
        f"{_HEADER_RESULTS}\n"
        f"\n"
        f"Событие с идентификатором `{DOMAIN}_{SERVICE_SET_DESCRIPTION}` и следующими значениями:\n"
        f"- `{ATTR_SUCCESS}: bool` - Если установка описания была выполнена успешно\n"
        f"- `{ATTR_DESCRIPTION}: str | None` - Описание, с которым была вызвана служба\n"
        f"- `{ATTR_PREVIOUS}: str | None` - Описание, которым обладал (или, в случае ошибки, обладает) лицевой счёт\n"
        f"- `{ATTR_ACCOUNT_ID}: int` - Внутренний идентификатор лицевого счёта\n"
        f"- `{ATTR_ACCOUNT_CODE}: str` - Номер лицевого счёта\n"
    )


def _get_yaml_configuration() -> str:
    output = StringIO()
    output.write("### Описание конфигурационной схемы\n")
    output.write(
        "```yaml\n"
        "# Файл `configuration.yaml`\n"
        f"{DOMAIN}:\n"
        f"\n"
        f"  # Тип выбранного ЛК\n"
        f"  # Значение по умолчанию: {API_TYPE_DEFAULT}\n"
        f"  # Перечень возможных значений:\n"
    )
    for type_, type_name in API_TYPE_NAMES.items():
        output.write(f"  # - {type_} ({type_name})\n")
    output.write(
        f'  {CONF_TYPE}: "..."\n'
        f"\n"
        f"  # Имя пользователя\n"
        f"  # Обязательный параметр\n"
        f'  {CONF_USERNAME}: "..."\n'
        f"\n"
        f"  # Пароль\n"
        f"  # Обязательный параметр\n"
        f'  {CONF_PASSWORD}: "..."\n'
        f"\n"
        f"  # Конфигурация по умолчанию для лицевых счетов\n"
        f"  # Необязательный параметр\n"
        f"  #"
        f"  # Данная конфигурация применяется, если отсутствует"
        f"  # конкретизация, указанная в разделе `{CONF_ACCOUNTS}`.\n"
        f"  {CONF_DEFAULT}:\n"
    )
    output.write(
        f"\n"
        f"    # Получать ли ссылки на логотипы\n"
        f"    # Значение по умолчанию: истина (true)\n"
        f"    {CONF_LOGOS}: true | false\n"
    )
    for (stuff_name, stuff_type) in chain((ACCOUNT_ENT_TYPE,), SUPPORT_TYPES.values()):
        if stuff_type is None:
            continue
        output.write(
            f"\n"
            f"    # Добавлять ли объект(-ы): {stuff_name}\n"
            f"    # Значение по умолчанию: истина (true)\n"
            f"    {stuff_type}: true | false\n"
        )
    output.write(
        f"\n"
        f"  # Настройки для отдельных лицевых счетов\n"
        f"  # Необязательный параметр\n"
        f"  {CONF_ACCOUNTS}:\n"
        f"\n"
        f"    # Номер лицевого счёта\n"
        f'    "...":\n'
        f"\n"
        f"      # Конфигурация по конкретным лицевым счетам выполняется аналогично\n"
        f"      # конфигурации по умолчанию для лицевых счетов (раздел `{CONF_DEFAULT}`).\n"
        f"      ...\n"
        f"```"
        f"\n\n"
    )
    entry_schema = CONFIG_ENTRY_SCHEMA.validators[-1].validators[-1].schema

    output.write(
        '### Вариант конфигурации "Чёрный список"\n'
        "\n"
        "Для реализации белого списка, конфигурация выполняется следующим образом:\n"
        "```yaml\n"
        "...\n"
        f"{DOMAIN}:\n"
        f"  ...\n"
        f"  # Выборочное исключение лицевых счетов\n"
        f"  {CONF_ACCOUNTS}:\n"
        f"    # Все указанные ниже лицевые счета будут добавлены\n"
        f'    "12345-678-90": false\n'
        f'    "98765-432-10": false\n'
        f'    "111000111000": false\n'
        f"```\n"
        f"\n"
    )

    output.write(
        '### Вариант конфигурации "Белый список"\n'
        "\n"
        "Для реализации белого списка, конфигурация выполняется следующим образом:\n"
        "```yaml\n"
        "...\n"
        f"{DOMAIN}:\n"
        f"  ...\n"
        f"  # Отключение добавление лицевых счетов по умолчанию\n"
        f"  {CONF_DEFAULT}: false\n"
        f"\n"
        f"  # Выборочное включение лицевых сченов\n"
        f"  {CONF_ACCOUNTS}:\n"
        f"    # Все указанные ниже лицевые счета будут добавлены\n"
        f'    "12345-678-90": true\n'
        f'    "98765-432-10": true\n'
        f'    "111000111000": true\n'
        f"```\n"
        f"\n"
        f"Также возможно использовать укороченную запись:\n"
        f"```yaml\n"
        f"...\n"
        f"{DOMAIN}:\n"
        f"  ...\n"
        f"  # Данный пример функционально эквивалентен предыдущему примеру\n"
        f"  {CONF_DEFAULT}: false\n"
        f'  {CONF_ACCOUNTS}: ["12345-678-90", "98765-432-10", "111000111000"]\n'
        f"```\n"
        f"\n"
    )

    for key, validator in entry_schema.items():
        print(key, validator)

    return output.getvalue()


def make_readme(file: TextIO, template: str):
    replacements = {
        "service_push_indications": _get_service_push_indications(),
        "service_calculate_indications": _get_service_calculate_indications(),
        "service_get_payments": _get_service_get_payments(),
        "service_get_invoices": _get_service_get_invoices(),
        "service_set_description": _get_service_set_description(),
        "gui_configuration": _get_gui_configuration(),
        "yaml_configuration": _get_yaml_configuration(),
        "providers_content": _get_providers_content(),
    }

    for replacement_id, value in replacements.items():
        template = template.replace(f"%%{replacement_id}%%", value)

    template = re.sub(r"\n{3,}", "\n\n", template)

    file.write(template)


def main():
    with open("README.md", "w", encoding="utf-8", newline="\n") as f:
        with open("README.template.md", "r", encoding="utf-8") as tpl:
            make_readme(f, tpl.read())

    exit(0)

    while True:
        try:
            routine_collect_images(ROOT_IMAGES)
            break
        except KeyboardInterrupt:
            print("RESTART")


if __name__ == "__main__":
    main()
