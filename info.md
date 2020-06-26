# Мосэнергосбыт для HomeAssistant
[![GitHub Page](https://img.shields.io/badge/GitHub-alryaz%2Fhass--mosenergosbyt-blue)](https://github.com/alryaz/hass-mosenergosbyt)
[![Donate Yandex](https://img.shields.io/badge/Donate-Yandex-red.svg)](https://money.yandex.ru/to/410012369233217)
[![Donate PayPal](https://img.shields.io/badge/Donate-Paypal-blueviolet.svg)](https://www.paypal.me/alryaz)
{% set mainline_num_ver = version_available.replace("v", "").replace(".", "") | int %}{%- set features = {
    'v0.2.6': 'Возможность отображения уведомлений при успешных вызовах служб',
    'v0.2.5': 'Отображение переданных за сегодня показаний (только МЭС)',
    'v0.2.4': '**Возможность предварительно подсчитывать стоимость по показаниям, и отдельно передавать показания напрямую в МЭС**',
    'v0.2.3': 'Установка произвольного User Agent для запросов; улучшение авторизации',
    'v0.2.2': 'Отображение стоимость ТО "ВКГО"; показ дат начала и конца периода (включительных) для МЭС',
    'v0.2.0': 'Major architecture overhaul in preparation for new account types support (MES+TKO available already), invoices sensors, progress made towards integrating submissions',
    'v0.1.1': 'Форматирование названий объектов',
    'v0.1.0': 'Поддержка нескольких пользователей; настройка через меню "Интеграции"',
}-%}{%- set breaking_changes = namespace(header="Breaking Changes", changes={
    'v0.1.1': ['Account uses `account_code` attribute for its number instead of `number`']
}) -%}{%- set bug_fixes = namespace(header="Bug fixes", changes={
    'v0.2.6': ['Расширены способы получения переданных показаний из ЛК'],
    'v0.2.5': ['Исправлено ложное отсутствие последних переданных показаний за текущий период'],
    'v0.2.3': ['Fixed unnecessary error verbosity', 'Fixed `info.md` duplicate headers'],
    'v0.2.2': ['Fixed non-negative value display for MES+TKO accounts'],
    'v0.2.1': ['Fixed reauthentication issue on network failure / server timeout']
}) -%}
{% if installed %}{% if version_installed == "master" %}
#### ⚠ Вы используете версию для разработки
This branch may be unstable, as it contains commits not tested beforehand.  
Please, do not use this branch in production environments.
{% else %}{% if version_installed == version_available %}
#### ✔ Вы используете актуальную версию{% else %}{% set num_ver = version_installed.replace("v", "").replace(".","") | int %}
#### 🚨 Вы используете устаревшую версию{% if num_ver < 20 %}
{% for ver, changes in breaking_changes.changes.items() %}{% set ver = ver.replace("v", "").replace(".","") | int %}{% if num_ver < ver %}{% if breaking_changes.header %}
##### {{ breaking_changes.header }} (`{{ version_installed }}` -> `{{ version_available }}`){% set breaking_changes.header = None %}{% endif %}{% for change in changes %}
{{ '- '+change }}{% endfor %}{% endif %}{% endfor %}
{% endif %}{% endif %}

{% for ver, fixes in bug_fixes.changes.items() %}{% set ver = ver.replace("v", "").replace(".","") | int %}{% if num_ver < ver %}{% if bug_fixes.header %}
##### {{ bug_fixes.header }} (`{{ version_installed }}` -> `{{ version_available }}`){% set bug_fixes.header = None %}{% endif %}{% for fix in fixes %}
{{ '- ' + fix }}{% endfor %}{% endif %}{% endfor %}

##### Features{% for ver, text in features.items() %}{% set feature_ver = ver.replace("v", "").replace(".", "") | int %}
- {% if num_ver < feature_ver %}**{% endif %}`{{ ver }}` {% if num_ver < feature_ver %}NEW** {% endif %}{{ text }}{% endfor %}

Please, report all issues to the [project's GitHub issues](https://github.com/alryaz/hass-mosenergosbyt/issues).
{% endif %}{% else %}
## Features{% for ver, text in features.items() %}
- {{ text }} _(supported since `{{ ver }}`)_{% endfor %}
{% endif %}
## Скриншоты
(Возможно увеличить, нажав на картинку и перейдя по ссылке)

[<img alt="Лицевой счёт" src="https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/account.png" height="240">](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/account.png)
[<img alt="Счётчик МЭС" src="https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/meter.png" height="240">](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/meter.png)
[<img alt="Счётчик МЭС+ТКО" src="https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/meter_tko.png" height="240">](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/meter_tko.png)
[<img alt="Квитанция" src="https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/invoice.png" height="240">](https://raw.githubusercontent.com/alryaz/hass-mosenergosbyt/master/images/invoice.png)

## Установка
### Посредством HACS
1. Откройте HACS (через `Extensions` в боковой панели)
1. Добавьте новый произвольный репозиторий:
   1. Выберите `Integration` (`Интеграция`) в качестве типа репозитория
   1. Введите ссылку на репозиторий: `https://github.com/alryaz/hass-mosenergosbyt`
   1. Нажмите кнопку `Add` (`Добавить`)
   1. Дождитесь добавления репозитория (занимает до 10 секунд)
   1. Теперь вы должны видеть доступную интеграцию `Mosenergosbyt (Мосэнергосбыт)` в списке новых интеграций.
1. Нажмите кнопку `Install` чтобы увидеть доступные версии
1. Установите последнюю версию нажатием кнопки `Install`
1. Перезапустите HomeAssistant

_Примечание:_ Не рекомендуется устанавливать ветку `master`. Она используется исключительно для разработки. 

### Вручную
Клонируйте репозиторий во временный каталог, затем создайте каталог `custom_components` внутри папки конфигурации
вашего HomeAssistant (если она еще не существует). Затем переместите папку `mosenergosbyt` из папки `custom_components` 
репозитория в папку `custom_components` внутри папки конфигурации HomeAssistant.
Пример (при условии, что конфигурация HomeAssistant доступна по адресу `/mnt/homeassistant/config`) для Unix-систем:
```
git clone https://github.com/alryaz/hass-mosenergosbyt.git hass-mosenergosbyt
mkdir -p /mnt/homeassistant/config/custom_components
mv hass-mosenergosbyt/custom_components/mosenergosbyt /mnt/homeassistant/config/custom_components
```

## Конфигурация
### Через интерфейс HomeAssistant
1. Откройте `Настройки` -> `Интеграции`
1. Нажмите внизу справа страницы кнопку с плюсом
1. Введите в поле поиска `Mosenergosbyt` или `Мосэнергосбыт`
   1. Если по какой-то причине интеграция не была найдена, убедитесь, что HomeAssistant был перезапущен после
        установки интеграции.
1. Выберите первый результат из списка
1. Введите данные вашей учётной записи для ЛК _"Мосэнергосбыт"_
1. Нажмите кнопку `Продолжить`
1. Через несколько секунд начнётся обновление; проверяйте список ваших объектов на наличие
   объектов, чьи названия начинаются на `MES`.

### Через `configuration.yaml`
#### Базовая конфигурация
Для настройки данной интеграции потребуются данные авторизации в ЛК Мосэнергосбыт.  
`username` - Имя пользователя (телефон / адрес эл. почты)  
`password` - Пароль
```yaml
mosenergosbyt:
  username: !secret mosenergosbyt_username
  password: !secret mosenergosbyt_password
```

#### Несколько пользователей
Возможно добавить несколько пользователей.
Для этого вводите данные, используя пример ниже:
```yaml
mosenergosbyt:
    # First account
  - username: !secret first_mosenergosbyt_username
    password: !secret first_mosenergosbyt_password

    # Second account
  - username: !secret second_mosenergosbyt_username
    password: !secret second_mosenergosbyt_password

    # Third account
  - username: !secret third_mosenergosbyt_username
    password: !secret third_mosenergosbyt_password 
```

#### Обновление конкретных лицевых счетов
##### **Вариант А:** Укажите список лицевых счетов:
```yaml
mosenergosbyt:
  ...
  # Список лицевых счетов
  accounts: ['99999-999-99', '88888-888-88']
```
##### **Вариант Б:** Дополнительно отфильтровать счётчики:
```yaml
mosenergosbyt:
  ...
  accounts:
    # Номер ЛС -> Номер счётчика
    99999-999-99: 123456789
    88888-888-88: ['321987654', '456789123']
```

#### Изменение интервалов обновления
Частота обновления данных (`scan_interval`) по умолчанию: 1 час  
Частота обновления авторизации (`login_timeout`) по умолчанию: 1 час
```yaml
mosenergosbyt:
  ...
  # Интервал обновления данных
  scan_interval:
    hours: 6
    seconds: 3
    minutes: 1
    ...

  # ... также возможно задать секундами
  scan_interval: 21600

  # Сбрасывать сессию после определённого времени
  # Сессия обновляется при следующем обновлении ЛС
  login_timeout:
    hours: 3
```

#### Настройка квитанций
Квитанции обновляются вместе с остальными объектами. Они отображают последние квитанции, выставленые
компанией. **То, что уже было уплачено, не отображается!** Существование данных объектов обусловлено
использованием их в качестве держателей информации для получения разброса цен.
```yaml
mosenergosbyt:
  ...
  # Включить квитанции для всех лицевых счетов
  invoices: true

  # Включить квитанции для конкретных лицевых счетов
  invoices: ['1131241222']

  # Отключить квитанции для всех счетов
  invoices: false
```

#### Настройка имён объектов
На данный момент, именование объектов происходит используя метод `str.format(...)` языка Python. Изменение следующих
параметров влияет на ID создаваемых объектов и их имена.

Поддерживаемые замены: `code`

Формат аккаунта (`account_name`) по умолчанию: `MES Account {code}`  
Формат счётчика (`meter_name`) по умолчанию: `MES Meter {code}`  
Формат квитанции (`invoice_name`) по умолчанию: `MES Invoice {code}`
```yaml
mosenergosbyt:
  ...
  # Произвольный формат для лицевых счетов
  account_name: 'Мой супер {code} лицевой счёт' 

  # Произвольный формат для счётчиков
  meter_name: 'Счётчик {code} жахает'

  # Произвольный формат для квитанций
  meter_name: 'За {code} платим много!'
```

####<a name="calculate_indications"></a> Подсчёт начислений до передачи показаний
> Только для электрических счётчиков Мосэнергосбыт

Компонент позволяет запускать службу `mosenergosbyt.calculate_indications` с параметрами:
- `entity_id`: Идентификатор сенсора счётчика (не совместимо с `meter_code`)
- `meter_code`: Номер счётчика (не совместимо с `entity_id`)
- `indications`: Список значений по показаниям (список длиной количества тарифов целевого счётчика из целых
   или дробных чисел)
- `ignore_period`: Не учитывать ограничения по периоду (по умолчанию `false` - учитывать)
- `incremental`: Прибавлять указанные значения поверх последних переданных <sup>1</sup>

которая в случае успешного вызова отсылает событие `mosenergosbyt_calculation_result`, содержащее следующие данные:
- `entity_id`: Идентификатор сенсора счётчика
- `meter_code`: Номер счётчика
- `indications`: Нормальзованный<sup>2</sup> список значений показаний из запроса
- `period`: Период (как правило начало месяца в Московском часовом поясе)
- `charged`: Числовое значение начисления (с десятичными цифрами)
- `indications_dict`: Именованый массив в фомате `t<число>` -> `<показание>`
- `comment`: Текстовый комментарий, сообщаемый сервером ЛК

<sup>1</sup> Последние переданные показания включают в себя те, что отображаются под `submitted_value_t[1,2,3]`  
<sup>2</sup> Будут возвращены значения, полученные после прибавления последних предыдущих показаний

Данная служба автоматически определяет попытку передать показания за пределами указанного срока и с недостаточным
количеством показаний. Проверку периода возможно отключить, _**ОДНАКО ДЕЛАТЬ ЭТО НАСТОЯТЕЛЬНО НЕ РЕКОМЕНДУЕТСЯ**_ в связи
с возможными отрицательными последствиями.

Ниже указан пример вызова службы:
{% raw %}
```yaml
service: mosenergosbyt.calculate_indications
data_template:
  entity_id: sensor.mes_meter_123456789
  indications:
    - "{{ states('sensor.monthly_consumption_peak') + state_attr('sensor.mes_meter_123456789', 'last_value_t1') }}"
    - "{{ states('sensor.monthly_consumption_offpeak') + state_attr('sensor.mes_meter_123456789', 'last_value_t2') }}"
    - "{{ states('sensor.monthly_consumption_halfpeak') + state_attr('sensor.mes_meter_123456789', 'last_value_t3') }}"
```
{% endraw %}

Ниже указан пример автоматизации, использующий данную возможность:
{% raw %}
```yaml
automation:
  - id: respond_to_calculation
    trigger:
      platform: event
      event_type: calculation_result
    action:
      service: persistent_notification.create
      data_template:
        title: "Результаты подсчётов"
        message: >
          Для счётчика {{ state_attr(trigger.event.data['entity_id'], 'meter_code') }}
          выполнен подсчёт за период {{ trigger.event.data['period'] }};
          будет начислено {{ trigger.event.data['charged'] }}
```
{% endraw %}

#### Передача показаний
> Только для электрических счётчиков Мосэнергосбыт

Компонент позволяет запускать службу `mosenergosbyt.push_indications` с параметрами:
- `entity_id`: Идентификатор сенсора счётчика (не совместимо с `meter_code`)
- `meter_code`: Номер счётчика (не совместимо с `entity_id`)
- `indications`: Список значений по показаниям (список длиной количества тарифов целевого счётчика из целых
   или дробных чисел)
- `ignore_period`: Не учитывать ограничения по периоду (по умолчанию `false` - учитывать)
- `incremental`: Прибавлять указанные значения поверх последних переданных <sup>3</sup>

которая в случае успешного вызова отсылает событие `mosenergosbyt_push_result`, содержащее следующие данные:
- `entity_id`: Идентификатор сенсора счётчика
- `meter_code`: Номер счётчика
- `indications`: Нормальзованный<sup>4</sup> список значений показаний из запроса
- `comment`: Текстовый комментарий, сообщаемый сервером ЛК

<sup>3</sup> Последние переданные показания включают в себя те, что отображаются под `submitted_value_t[1,2,3]`  
<sup>4</sup> Будут возвращены значения, полученные после прибавления последних предыдущих показаний

Данная служба автоматически определяет попытку передать показания за пределами указанного срока и с недостаточным
количеством показаний. Проверку периода возможно отключить, _**ОДНАКО ДЕЛАТЬ ЭТО НАСТОЯТЕЛЬНО НЕ РЕКОМЕНДУЕТСЯ**_ в связи
с возможными отрицательными последствиями. Пример таких последствий: внеочередное создание квитанции,
содержащее в себе двойную плату.

Вызов передачи показаний и его обработка аналогичны операции [предварительного подсчёта](#calculate_indications).

#### Использование другого "браузера" (UA) в запросах
По умолчанию модуль `fake_useragent` ([ссылка](https://pypi.org/project/fake-useragent/)) пробует создать
уникальный заголовок `User-Agent` для использования на протяжении всего существования объекта работы с API.
Если желаемо указание статичного заголовка, это возможно используя пример ниже:
```yaml
mosenergosbyt:
  ...
  # Произвольный User-Agent
  user_agent: 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.2 (KHTML, like Gecko) Chrome/22.0.1216.0 Safari/537.2'
  
  # Тот же самый User-Agent, но в несколько строк
  user_agent: >
    Mozilla/5.0 (Windows NT 6.1)
    AppleWebKit/537.2 (KHTML, like Gecko)
    Chrome/22.0.1216.0
    Safari/537.2
