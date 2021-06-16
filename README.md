_ЕЛК ЖКХ &#xab;Интер РАО&#xbb; для Home Assistant_
==================================================
<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/master/images/header.png">

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

## Скриншоты
![Сенсоры, часть 1](https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/sensors_1.png)
![Сенсоры, часть 2](https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/sensors_2.png)
![Сенсоры, часть 3](https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/sensors_3.png)

## Установка
### Посредством HACS
> **✔️️ Рекомендуемый метод**
1. Установите HACS ([инструкция по установке на оф. сайте](https://hacs.xyz/docs/installation/installation/))
2. Добавьте репозиторий в список дополнительных
3. Найдите `energosbyt` в поиске по интеграциям <sup>1</sup>
4. Установите последнюю версию компонента, нажав на кнопку `Установить` (`Install`)
5. Перезапустите Home Assistant

_<sup>1</sup> При поиске может появится компонент `Мосэнергосбыт`. Это предшествующая данному
проекту интеграция, и будет в скором времени упразднена._

### Вручную
> **⚠️ Не рекомендуется**
1. Скачайте архив с исходным кодом дополнения
2. Извлеките папку `lkcomu_interrao` из архива в папку `custom_components` внутри
   папки с конфигурацией Home Assistant (создайте её, если она отсутствует)
3. Перезапустите Home Assistant

## Конфигурация
Конфигурация компонента доступна несколькими способами.

> **Внимание:** конфигурации через интерфейс носят императивный характер.
> Интеграция, добавленная через интерфейс, исключит загрузку конфигурации
> из YAML при совпадении пар из имени пользователя (`username`) и типа ЛК (`type`).

### Посредством YAML
Конфигурация через YAML раскрывает дополнительные возможности, и позволяет
более детально настраивать интеграцию.

#### Для одной учётной записи
```yaml
# Файл configuration.yaml
...

lkcomu_interrao:
  username: username1
  password: password1
```

#### Для нескольких учётных записей
```yaml
# Файл configuration.yaml
...

lkcomu_interrao:
  # По умолчанию используется ЕЛК Мосэнергосбыт
  - username: username1
    password: password1

  # Чтобы использовать другой ЕЛК, задайте значение параметру `type`
  - type: altai
    username: username2
    password: password2

  # Использование одного и того же имени пользователя возможно
  # для разных типов поставщиков.
  - type: volga
    username: username2
    password: password2
```

## Службы
### `lkcomu_interrao.submit_indications` &mdash; Передача показаний
> @ TODO @

### `lkcomu_interrao.calculate_indications` &mdash; Подсчёт начислений
> @ TODO @

### `lkcomu_interrao.api_refresh` &mdash; Обновление данных API
> @ TODO @

### `lkcomu_interrao.set_description` &mdash; Установить описание лицевого счёта
> @ TODO @

## Поддерживаемые ЛК

Ниже предъявлен перечень поддерживаемых ЛК с их внутренними идентификаторами.
Данные идентификаторы используются как значение для поля `type`.

> **Внимание:** Поддерживаются только ЛК физических лиц. Поддержка ЛК юридических лиц не планируется.

### Алтайэнергосбыт &mdash; `altai`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/altai.png" height="50" alt="ЕЛК ЖКХ ССК">](https://lkfl.altaiensb.com)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам

#### Пример конфигурации:
```yaml
...
lkcomu_interrao:
  type: altai
  username: username1
  password: password1
```

### Башэлектросбыт &mdash; `bashkortostan`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/bashkortostan.png" height="50" alt="ЕЛК ЖКХ ССК">](https://lkk.bashesk.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам

#### Пример конфигурации:
```yaml
...
lkcomu_interrao:
  type: bashkortostan
  username: username1
  password: password1
```

### Мосэнергосбыт &mdash; `moscow`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/moscow.png" height="50" alt="ЕЛК ЖКХ ССК">](https://my.mosenergosbyt.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков<sup>1</sup>
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам<sup>2</sup>

_<sup>1</sup> Для поставщика ТКО может применяться виртуализация счётчика_<br>
_<sup>2</sup> На данный момент только для Мосэнергосбыт и МосОблЕИРЦ_

#### Пример конфигурации:
```yaml
...
lkcomu_interrao:
  type: moscow
  username: username1
  password: password1
```

### Орловский Энергосбыт &mdash; `oryol`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/oryol.png" height="50" alt="ЕЛК ЖКХ ССК" >](https://my.interrao-orel.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам

#### Пример конфигурации:
```yaml
...
lkcomu_interrao:
  type: oryol
  username: username1
  password: password1
```

### Саратовэнерго &mdash; `saratov`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/saratov.png" height="50" alt="ЕЛК ЖКХ ССК">](https://my.saratovenergo.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам

#### Пример конфигурации:
```yaml
...
lkcomu_interrao:
  type: saratov
  username: username1
  password: password1
```


### Северная Сбытовая Компания (ССК) &mdash; `sevesk`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/sevesk.png" height="50" alt="ЕЛК ЖКХ ССК">](https://lk.sevesk.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам

#### Пример конфигурации:
```yaml
...
lkcomu_interrao:
  type: sevesk
  username: username1
  password: password1
```

### Тамбовская Энергосбытовая Компания (ТЭСК) &mdash; `tambov`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/tambov.png" height="50" alt="ЕЛК ЖКХ ССК">](https://my.tesk.su/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам

#### Пример конфигурации:
```yaml
...
lkcomu_interrao:
  type: tambov
  username: username1
  password: password1
```

### Томскэнергосбыт &mdash; `tomsk`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/tomsk.png" height="50" alt="ЕЛК ЖКХ ССК">](https://my.tomskenergosbyt.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков<sup>1</sup>
- Отображение последних квитанций
- Отображение последних платежей<sup>1</sup>
- Передача показаний по счётчикам<sup>1</sup>

_<sup>1</sup> На данный момент только АО "Томскэнергосбыт"_

#### Пример конфигурации:
```yaml
...
lkcomu_interrao:
  type: tomsk
  username: username1
  password: password1

  # Дополнительные параметры (необязательно):
  # Данные параметры влияют на все учётные записи под профилем.
  
  # Отображние только данных от АО "Томскэнергосбыт" (не влияет на квитанции)
  byt_only: false
```

### Энергосбыт Волга - `volga`
[<img src="https://raw.githubusercontent.com/alryaz/hass-lkcomu-interrao/main/images/headers/volga.png" height="50" alt="ЕЛК ЖКХ ССК">](https://my.esbvolga.ru/)

#### Поддерживается:
- Отображение дополнительной информации об учётной записи
- Отображение счётчиков
- Отображение последних квитанций
- Отображение последних платежей
- Передача показаний по счётчикам

#### Пример конфигурации:
```yaml
...
lkcomu_interrao:
  type: volga
  username: username1
  password: password1
```

## Дополнительная информация
> @ TODO @
