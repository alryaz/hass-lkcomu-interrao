_ЕЛК ЖКХ &#xab;Интер РАО&#xbb;_ для _Home Assistant_
==================================================
<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/master/images/header.png" alt="Логотип интеграции">

> Предоставление информации о текущем состоянии ваших аккаунтов в ЕЛК ЖКХ.
>
>[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
>[![Лицензия](https://img.shields.io/badge/%D0%9B%D0%B8%D1%86%D0%B5%D0%BD%D0%B7%D0%B8%D1%8F-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
>[![Поддержка](https://img.shields.io/badge/%D0%9F%D0%BE%D0%B4%D0%B4%D0%B5%D1%80%D0%B6%D0%B8%D0%B2%D0%B0%D0%B5%D1%82%D1%81%D1%8F%3F-%D0%B4%D0%B0-green.svg)](https://github.com/alryaz/hass-lkcomu-interrao/graphs/commit-activity)
>
>[![Пожертвование Yandex](https://img.shields.io/badge/%D0%9F%D0%BE%D0%B6%D0%B5%D1%80%D1%82%D0%B2%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5-Yandex-red.svg)](https://money.yandex.ru/to/410012369233217)
>[![Пожертвование PayPal](https://img.shields.io/badge/%D0%9F%D0%BE%D0%B6%D0%B5%D1%80%D1%82%D0%B2%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5-Paypal-blueviolet.svg)](https://www.paypal.me/alryaz)

## Введение
> @ TODO @

## Установка
### Посредством HACS
> **✔️️ Рекомендуемый метод**
1. Установите HACS ([инструкция по установке на оф. сайте](https://hacs.xyz/docs/installation/installation/))
2. Добавьте репозиторий в список дополнительных
3. Найдите `energosbyt` в поиске по интеграциям <sup>1</sup>
4. Установите последнюю версию компонента, нажав на кнопку `Установить` (`Install`)
5. Перезапустите Home Assistant

_<sup>1</sup> При поиске может появиться компонент `Мосэнергосбыт`. Это предшествующая данному
проекту интеграция, и будет в скором времени упразднена._

### Вручную
> **⚠️ Не рекомендуется**
1. Скачайте архив с исходным кодом дополнения
2. Извлеките папку `lkcomu_interrao` из архива в папку `custom_components` внутри
   папки с конфигурацией Home Assistant (создайте её, если она отсутствует)
3. Перезапустите Home Assistant

## Настройка

### Через раздел интеграции
1. Перейдите в подраздел _"[Интеграции](https://my.home-assistant.io/redirect/integrations)"_ в разделе _"Настройки"_
2. Нажмите кнопку _"Добавить интеграцию"_
3. Введите в поисковую строку: **_Личный кабинет Интер РАО (Энергосбыт)_** (англ. **_Inter RAO Personal Cabinet (Energosbyt)_**)
4. Выберите найденную интеграцию
5. Следуйте инструкциям мастера по добавлению

_Примечание:_ Поле **_Заголовок User-Agent_** (англ. **_User-Agent header_**) генерируется автоматически.

### Описание конфигурационной схемы
```yaml
# Файл `configuration.yaml`
lkcomu_interrao:

  # Тип выбранного ЛК
  # Значение по умолчанию: moscow
  # Перечень возможных значений:
  # - altai (ЛК Алтай (АО «АлтайЭнергосбыт»))
  # - bashkortostan (ЛКК ЭСКБ (Башэлектросбыт))
  # - moscow (ЕЛК ЖКХ (АО «Мосэнергосбыт», МосОблЕИРЦ, ПАО «Россети Московский регион»))
  # - oryol (ЛКК Орел (ООО «Орловский энергосбыт»))
  # - saratov (ЛК Саратов (ПАО «Саратовэнерго»))
  # - sevesk (ЕЛК Вологда (Северная сбытовая компания))
  # - tambov (ЛК ТЭСК (Тамбовская энергосбытовая компания))
  # - tomsk (ЕЛК Томск (Томскэнергосбыт / Томск РТС))
  # - volga (ЛКК ЭСВ (Энергосбыт Волга))
  type: "..."

  # Имя пользователя
  # Обязательный параметр
  username: "..."

  # Пароль
  # Обязательный параметр
  password: "..."

  # Конфигурация по умолчанию для лицевых счетов
  # Необязательный параметр
  #  # Данная конфигурация применяется, если отсутствует  # конкретизация, указанная в разделе `accounts`.
  default:

    # Получать ли ссылки на логотипы
    # Значение по умолчанию: истина (true)
    logos: true | false

    # Добавлять ли объект(-ы): Информация о лицевом счёте
    # Значение по умолчанию: истина (true)
    accounts: true | false

    # Добавлять ли объект(-ы): Счётчик коммунальных услуг
    # Значение по умолчанию: истина (true)
    meters: true | false

    # Добавлять ли объект(-ы): Последний зарегистрированный платёж
    # Значение по умолчанию: истина (true)
    last_payment: true | false

    # Добавлять ли объект(-ы): Последняя выпущенная квитанция
    # Значение по умолчанию: истина (true)
    last_invoice: true | false

  # Настройки для отдельных лицевых счетов
  # Необязательный параметр
  accounts:

    # Номер лицевого счёта
    "...":

      # Конфигурация по конкретным лицевым счетам выполняется аналогично
      # конфигурации по умолчанию для лицевых счетов (раздел `default`).
      ...
```

### Вариант конфигурации "Чёрный список"

Для реализации белого списка, конфигурация выполняется следующим образом:
```yaml
...
lkcomu_interrao:
  ...
  # Выборочное исключение лицевых счетов
  accounts:
    # Все указанные ниже лицевые счета будут добавлены
    "12345-678-90": false
    "98765-432-10": false
    "111000111000": false
```

### Вариант конфигурации "Белый список"

Для реализации белого списка, конфигурация выполняется следующим образом:
```yaml
...
lkcomu_interrao:
  ...
  # Отключение добавление лицевых счетов по умолчанию
  default: false

  # Выборочное включение лицевых сченов
  accounts:
    # Все указанные ниже лицевые счета будут добавлены
    "12345-678-90": true
    "98765-432-10": true
    "111000111000": true
```

Также возможно использовать укороченную запись:
```yaml
...
lkcomu_interrao:
  ...
  # Данный пример функционально эквивалентен предыдущему примеру
  default: false
  accounts: ["12345-678-90", "98765-432-10", "111000111000"]
```

## Доступные объекты

Все объекты гарантируют наличие и полноту следующих атрибутов:
- `account_code: str` - Номер лицевого счёта
- `account_id: int` - Внутренний идентификатор лицевого счёта

### Лицевые счета &mdash; `lkcomu_interrao_account`
> **Домен объектов:** `sensor`

Объект лицевого счёта отображает основную информацию о лицевом счёте, а также его баланс
(положительное значение) или имеющуюся задолженность (отрицательное значение) <sup>1</sup>.

Состояние объекта может принимать следующие значения:
- `unknown` - Информация о состоянии баланса не была предоставлена
- _число_ - Текущее состояние баланса

_<sup>1</sup> ... в том случае, если лицевой счёт предоставляет информацию о балансе_  

### Счётчики &mdash; `lkcomu_interrao_meter`
> **Домен объектов:** `sensor`

Объект счётчика отображает информацию о счётчике, а также сведения о последних переданных
показаниях и диапазоне периода передачи показаний<sup>1</sup>.

Состояние объекта может принимать следующие значения:
- `ok` - Текстовое описание состояния отсутствует
- _текст_ - Текстовое описание состояние счётчика (может быть любой длины, и содержать в себе любой набор символов, в т.ч. HTML-теги)

Объект гарантирует наличие и полноту следующих атрибутов:
- `meter_code` - Номер счётчика
- `install_date` - Дата установки
- `submit_period_start` - Дата начала периода передачи показаний (в текущем месяце) <sup>1</sup>
- `submit_period_end` - Дата окончания периода передачи показаний (в текущем месяце) <sup>1</sup>
- `submit_period_active` - Флаг активности периода передачи показаний <sup>1</sup>
- `zone_t[N]_name` - Наименование тарифной зоны / тарифа
- `zone_t[N]_last_indication` - Последнее показание по тарифной зоне <sup>2</sup>

Объект гарантирует наличие, но не полноту следующих атрибутов:
- `model` - Модель счётчика
- `last_indications_date` - Дата последней передачи показаний
- `zone_t[N]_today_indication` - Значение переданного сегодня показания по тарифной зоне
- `zone_t[N]_invoice_indication` - Значение последнего показания по тарифной зоне, учтённому в квитанции
- `zone_t[N]_period_indication` - Значение переданного за период показания по тарифной зоне <sup>1</sup>
- `zone_t[N]_invoice_name` - Наименование тарифной зоны, указанное в последней квитанции

_<sup>1</sup> ... в том случае, если счётчик поддерживает передачу показаний_<br>
_<sup>2</sup> При отсутствии фактического значения атрибут примет значение `0.0`_

### Последние платежи &mdash; `lkcomu_interrao_last_payment`
> **Домен объектов:** `binary_sensor`

Объект последнего платежа отображает информацию о последнем зарегистрированном платеже,
связанном с лицевым счётом.

Состояние объекта может принимать следующие значения:
- `on` - Платёж был обработан
- `off` - Платёж ещё не обработан
- `unknown` - Последний платёж не был найден

Объект гарантирует наличие и полноту следующих атрибутов:
- `amount: float` - Сумма платежа
- `paid_at: str` - Дата и время платежа
- `period: str` - Период, за который был выполнен платёж

Объект гарантирует наличие, но не полноту, следующих атрибутов:
- `status: str | None` - Состояние платежа
- `agent: str | None` - Банк, проводящий платёж
- `group: str | None` - Группа платежа (для лицевых счетов с несколькими источниками платежей)

### Последние квитанции &mdash; `lkcomu_interrao_last_invoice`
> **Домен объектов:** `sensor`

> @ TODO @

## Службы
_**N.B.** Подразумевается, что домен служб - `lkcomu_interrao`_

### `submit_indications` &mdash; Передача показаний
> Только для объектов счётчиков, поддерживающих данный функционал

### `calculate_indications` &mdash; Подсчёт начислений
> Только для объектов счётчиков, поддерживающих данный функционал

### `set_description` &mdash; Установить описание лицевого счёта
> Только для объектов лицевых счетов

Устанавливает описание для лицевого счёта и провоцирует его обновление.

#### Параметры
- `description: str | None` - _(опционально)_ Новое описание для лицевого счёта

#### Результат
Событие с идентификатором `lkcomu_interrao_set_description` и следующими значениями:
- `success: bool` - Если установка описания была выполнена успешно
- `description: str | None` - Описание, с которым была вызвана служба
- `previous: str | None` - Описание, которым обладал (или, в случае ошибки, обладает) лицевой счёт
- `account_id: int` - Внутренний идентификатор лицевого счёта
- `account_code: str` - Номер лицевого счёта

## Поддерживаемые ЛК

Ниже предъявлен перечень поддерживаемых ЛК с их внутренними идентификаторами.
Данные идентификаторы используются как значение для поля `type`.

> **Внимание:** Поддерживаются только ЛК физических лиц. Поддержка ЛК юридических лиц не планируется.
### ЕЛК ЖКХ (АО «Мосэнергосбыт», МосОблЕИРЦ, ПАО «Россети Московский регион») - `moscow`
[![Ссылка на личный кабинет &quot;ЕЛК ЖКХ (АО «Мосэнергосбыт», МосОблЕИРЦ, ПАО «Россети Московский регион»)&quot;](https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/moscow.png)](https://my.mosenergosbyt.ru)

#### Пример конфигурации:

```yaml
...
lkcomu_interrao:
  type: moscow
  username: username1
  password: password1
```

#### Поставщик `MES` &mdash; Электричество
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/mes/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последний зарегистрированный платёж</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/mes/last_payment.png" alt="Скриншот">
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/mes/last_invoice.png" alt="Скриншот">
</details>
<details>
  <summary>Счётчик коммунальных услуг</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/mes/meters.png" alt="Скриншот">
</details>

#### Поставщик `KSG` &mdash; Электричество
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/ksg/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последний зарегистрированный платёж</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/ksg/last_payment.png" alt="Скриншот">
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/ksg/last_invoice.png" alt="Скриншот">
</details>
<details>
  <summary>Счётчик коммунальных услуг</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/ksg/meters.png" alt="Скриншот">
</details>

#### Поставщик `MOE` &mdash; ЕПД
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/moe/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последний зарегистрированный платёж</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/moe/last_payment.png" alt="Скриншот">
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/moe/last_invoice.png" alt="Скриншот">
</details>
<details>
  <summary>Счётчик коммунальных услуг</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/moe/meters.png" alt="Скриншот">
</details>

#### Поставщик `TKO` &mdash; ТКО
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/tko/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последний зарегистрированный платёж</summary> 
  Снимок экрана отсутствует
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/tko/last_invoice.png" alt="Скриншот">
</details>
<details>
  <summary>Счётчик коммунальных услуг</summary> 
  Снимок экрана отсутствует
</details>

### ЛКК Орел (ООО «Орловский энергосбыт») - `oryol`
[![Ссылка на личный кабинет &quot;ЛКК Орел (ООО «Орловский энергосбыт»)&quot;](https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/oryol.png)](https://my.interrao-orel.ru)

#### Пример конфигурации:

```yaml
...
lkcomu_interrao:
  type: oryol
  username: username1
  password: password1
```

#### Поставщик `ORL_EPD` &mdash; ЕПД
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/orl_epd/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/orl_epd/last_invoice.png" alt="Скриншот">
</details>

#### Поставщик `ORL` &mdash; Электричество
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/orl/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последний зарегистрированный платёж</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/orl/last_payment.png" alt="Скриншот">
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/orl/last_invoice.png" alt="Скриншот">
</details>
<details>
  <summary>Счётчик коммунальных услуг</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/orl/meters.png" alt="Скриншот">
</details>

### ЛКК ЭСВ (Энергосбыт Волга) - `volga`
[![Ссылка на личный кабинет &quot;ЛКК ЭСВ (Энергосбыт Волга)&quot;](https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/volga.png)](https://my.esbvolga.ru)

#### Пример конфигурации:

```yaml
...
lkcomu_interrao:
  type: volga
  username: username1
  password: password1
```

#### Поставщик `VLD` &mdash; Электричество
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/vld/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последний зарегистрированный платёж</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/vld/last_payment.png" alt="Скриншот">
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/vld/last_invoice.png" alt="Скриншот">
</details>
<details>
  <summary>Счётчик коммунальных услуг</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/vld/meters.png" alt="Скриншот">
</details>

### ЕЛК Томск (Томскэнергосбыт / Томск РТС) - `tomsk`
[![Ссылка на личный кабинет &quot;ЕЛК Томск (Томскэнергосбыт / Томск РТС)&quot;](https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/tomsk.png)](https://my.tomskenergosbyt.ru)

#### Пример конфигурации:

```yaml
...
lkcomu_interrao:
  type: tomsk
  username: username1
  password: password1
```

#### Поставщик `TMK_NRG` &mdash; generic
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/tmk_nrg/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последний зарегистрированный платёж</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/tmk_nrg/last_payment.png" alt="Скриншот">
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/tmk_nrg/last_invoice.png" alt="Скриншот">
</details>
<details>
  <summary>Счётчик коммунальных услуг</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/tmk_nrg/meters.png" alt="Скриншот">
</details>

### ЛК ТЭСК (Тамбовская энергосбытовая компания) - `tambov`
[![Ссылка на личный кабинет &quot;ЛК ТЭСК (Тамбовская энергосбытовая компания)&quot;](https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/tambov.png)](https://my.tesk.su)

#### Пример конфигурации:

```yaml
...
lkcomu_interrao:
  type: tambov
  username: username1
  password: password1
```

#### Поставщик `TMB` &mdash; Электричество
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/tmb/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последний зарегистрированный платёж</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/tmb/last_payment.png" alt="Скриншот">
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/tmb/last_invoice.png" alt="Скриншот">
</details>
<details>
  <summary>Счётчик коммунальных услуг</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/tmb/meters.png" alt="Скриншот">
</details>

### ЕЛК Вологда (Северная сбытовая компания) - `sevesk`
[![Ссылка на личный кабинет &quot;ЕЛК Вологда (Северная сбытовая компания)&quot;](https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/sevesk.png)](https://lk.sevesk.ru)

#### Пример конфигурации:

```yaml
...
lkcomu_interrao:
  type: sevesk
  username: username1
  password: password1
```

#### Поставщик `VLG` &mdash; Электричество
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/vlg/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последний зарегистрированный платёж</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/vlg/last_payment.png" alt="Скриншот">
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/vlg/last_invoice.png" alt="Скриншот">
</details>
<details>
  <summary>Счётчик коммунальных услуг</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/vlg/meters.png" alt="Скриншот">
</details>

### ЛК Саратов (ПАО «Саратовэнерго») - `saratov`
[![Ссылка на личный кабинет &quot;ЛК Саратов (ПАО «Саратовэнерго»)&quot;](https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/saratov.png)](https://my.saratovenergo.ru)

#### Пример конфигурации:

```yaml
...
lkcomu_interrao:
  type: saratov
  username: username1
  password: password1
```

#### Поставщик `SAR` &mdash; Электричество
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/sar/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последний зарегистрированный платёж</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/sar/last_payment.png" alt="Скриншот">
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/sar/last_invoice.png" alt="Скриншот">
</details>
<details>
  <summary>Счётчик коммунальных услуг</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/sar/meters.png" alt="Скриншот">
</details>

### ЛКК ЭСКБ (Башэлектросбыт) - `bashkortostan`
[![Ссылка на личный кабинет &quot;ЛКК ЭСКБ (Башэлектросбыт)&quot;](https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/bashkortostan.png)](https://lkk.bashesk.ru)

#### Пример конфигурации:

```yaml
...
lkcomu_interrao:
  type: bashkortostan
  username: username1
  password: password1
```

#### Поставщик `UFA` &mdash; Электричество
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/ufa/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последний зарегистрированный платёж</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/ufa/last_payment.png" alt="Скриншот">
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/ufa/last_invoice.png" alt="Скриншот">
</details>
<details>
  <summary>Счётчик коммунальных услуг</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/ufa/meters.png" alt="Скриншот">
</details>

### ЛК Алтай (АО «АлтайЭнергосбыт») - `altai`
[![Ссылка на личный кабинет &quot;ЛК Алтай (АО «АлтайЭнергосбыт»)&quot;](https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/altai.png)](https://lkfl.altaiensb.com)

#### Пример конфигурации:

```yaml
...
lkcomu_interrao:
  type: altai
  username: username1
  password: password1
```

#### Поставщик `ALT` &mdash; Электричество
Для поставщика реализована поддержка следующих объектов:
<details>
  <summary>Информация о лицевом счёте</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/alt/accounts.png" alt="Скриншот">
</details>
<details>
  <summary>Последний зарегистрированный платёж</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/alt/last_payment.png" alt="Скриншот">
</details>
<details>
  <summary>Последняя выпущенная квитанция</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/alt/last_invoice.png" alt="Скриншот">
</details>
<details>
  <summary>Счётчик коммунальных услуг</summary> 
  <img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/providers/alt/meters.png" alt="Скриншот">
</details>

## Дополнительная информация
> @ TODO @