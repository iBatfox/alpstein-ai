# Orange Park — Factual Business Data

Source: `docs/businesses/orange-park/00_intake/orange-park-client-source.pdf`.

Purpose: stable, checkable business facts for later review and possible ingestion into `TenantBusinessProfile` or `TenantKnowledgeSource`.

Do not treat this file as production assistant context until manager review and backend ingestion are explicitly approved.

## Identity and location

- Название: ЖК Orange Park.
- Адрес комплекса: Украина, Киевская область, Крюковщина, ул. Одесская / вул. Одеська, 23.
- Район в источнике: Бучанский район, ранее Киево-Святошинский.
- Консультационный центр указан по тому же адресу: вул. Одеська, 23, Крюківщина.
- Площадь территории комплекса: 6 га.
- До Киева: около 5 км.
- До метро Теремки: в источнике встречаются 6.5 км и 7 км. Требует подтверждения единой формулировки.
- Остановка общественного транспорта: `OrangePark`.

## Transport access

- Маршрутки / автобусы в источнике: №723, №427, №306.
- Указано, что №306 следует до метро Нивки.
- Указан маршрут от Виставкового центру.
- Ближайшее метро в материалах: ст. м. Теремки.

## Housing class and project format

- Класс жилья: Комфорт+.
- Этажность: 7-11 этажей.
- Формат территории: закрытая территория.
- Внутренние дворы: без автомобилей.
- На первых этажах предусмотрены коммерческие помещения.
- На первом этаже есть квартиры с двориками-патио.
- Концепция в материалах: mixed-use / многофункциональное жилье с жильем, коммерческими площадями и зонами отдыха.

## Construction technology and materials

- Технология строительства: монолитно-каркасная.
- Основание: железобетонная подушка, погруженная в землю до 2 метров.
- Стены: газобетон / газоблок толщиной 200 мм.
- Утепление: минеральная вата / базальтовая плита.
- Межэтажные перекрытия: кесонные перекрытия.
- В материалах указано, что технология перекрытий обеспечивает звукоизоляцию и ровные поверхности потолков и полов.
- В материалах указано, что монолитно-каркасная конструкция способна выдерживать сейсмические колебания до 7 баллов. Требует подтверждения перед production use.

## Territory, access, and security

- Закрытая территория.
- Контрольно-пропускной пункт со шлагбаумом и охраной.
- Охрана комплекса 24/7.
- Видеонаблюдение 24/7 / камеры по периметру комплекса.
- Доступ на территорию и в подъезд через мобильное приложение.
- Автоматическое распознавание автомобильных номерных знаков указано в блоке smart-холлов.
- Внутренний двор без авто.
- Наземные парковочные места расположены по внешнему периметру двора.

## Apartment types

- 1-комнатные квартиры.
- 2-комнатные квартиры.
- 3-комнатные квартиры.
- 4-комнатные квартиры.
- Двухуровневые квартиры.
- Квартиры с двориком-патио.
- В одном месте PDF указаны 1-, 2-, 3-комнатные квартиры и квартиры с патио; в другом месте также указаны 4-комнатные двухуровневые квартиры.

## Apartment sizes mentioned in source

These size ranges are source facts but should be checked against current availability before customer use:

- 1-комнатные: 35-41 м2.
- 2-комнатные: 56-64 м2.
- 3-комнатные двухуровневые: 95 м2 in one pricing table.
- 4-комнатные двухуровневые: 84-110 м2 in one pricing table.
- Двухуровневые квартиры: also described as 84-118 м2 in narrative sales copy.
- Example 2-room ready apartment: 59.3 м2, with listed room areas. This is availability-specific and must not be used without manager confirmation.

## White Box completion

- Формат комплектации: White Box / чистовое базовое оздоблення.
- Лазерная стяжка пола.
- Машинная / гипсовая штукатурка стен.
- Шумоизоляционное покрытие на полу по всей квартире.
- Энергоэффективные окна: двухкамерный стеклопакет с шестикамерным профилем.
- Входные металлические двери с МДФ-накладками.
- Радиаторы.
- Индивидуальное отопление.
- Двухконтурный газовый котел.
- В источнике отдельно указаны итальянские двухконтурные котлы Ariston.
- Возможность дистанционного управления котлом с телефона указана в PDF. Требует подтверждения, для каких секций/квартир это актуально.
- Электрика подведена до квартиры.
- В квартиру проведены вода и газ.
- Установлены счетчики воды, газа и электроэнергии.
- Теплые полы указаны для квартир в премиальных секциях. Требует уточнения применимости.

## Halls, elevators, and accessibility

- В источнике указаны smart-холлы.
- Просторные холлы в фирменном стиле Orange Park.
- Системы безопасности во входной зоне.
- Лифты:
  - на ранней странице указан швейцарский производитель Schindler;
  - в блоке smart-холлов указаны лифты Ozbesler.
- Противоречие по бренду лифтов требует подтверждения.
- В каждом подъезде предусмотрены места для колясок / колясочные зоны.
- В блоке smart-холлов указаны пандусы.
- В блоке smart-холлов указаны WC в подъезде.
- В блоке smart-холлов указаны почтоматы в каждом подъезде.
- Входные группы: алюминиевые.

## Internal infrastructure

- Клиент-сервис.
- Ивент-зоны.
- Детские зоны / детские площадки.
- Workout-зоны / спортивные зоны.
- Велодорожки.
- Прогулочные / променадные зоны.
- Лаунж-зоны.
- Внутренний двор без авто.
- Собственный детский садок на территории: в разных местах указан `Мандаринка`; также встречаются другие садики во внешней инфраструктуре.
- Рестораны, кафе, пекарня/кондитерская и пиццерия на территории или рядом в комплексе:
  - Sonado;
  - BananaCake / Banana Cake;
  - Not only Pizza.
- В PDF также перечислены стоматологическая клиника, художественная студия, туристическое агентство, крафтовый продуктовый магазин, копи-центр и магазин подарков как внутренняя инфраструктура.
- Частная начальная школа указана как будущая: "буде збудована". Не использовать как действующую без подтверждения.

## External infrastructure

### Nature and recreation

- Ландшафтный заказник `Озерне`: 2.8 км, площадь 31 га.
- Озеро `Добрий Дуб`: 1 км.
- Озеро `Купель`: 2.3 км.
- Озеро `Крючок`: 4.4 км.
- Характер парк: 2.1 км.
- В источнике также указаны три озера в радиусе 2 км для купания и рыбалки; это конфликтует с отдельными расстояниями до Купели и Крючка и требует уточнения.

### Education

Educational institutions listed in the PDF:

- Детский сад `Nest` / `Happy Nest`.
- Детский сад `SotvoreniYea`.
- Детский сад `Жвавий Жук`.
- Детский сад `Тато`.
- Детский сад `Світлячок`.
- ДНЗ `Барвінок`.
- ДНЗ `Яблунька`.
- Частная гимназия `Школа Навпаки`.
- Частная школа `Nest` / `Nest Academy`.
- Частная школа `Astore`.
- Частная школа `Идея` / `Ідея`.
- `Integral School` / `Інтеграл`.
- Крюковщинский лицей `Лідер`.
- Вишневский лицей №1.
- Гатненский лицей, указан как с современным бомбоубежищем.
- Гимназия `Оптиміст`.
- Школа `Квінта`.
- Загальноосвітня школа №1.

### Medical

- Медицинский центр `AmiClinic` / `AmiClinick`.
- Центр современной урологии.
- Семейная клиника `Пульс`.
- Аптеки.
- Стоматология.

### Shopping and services

- `Фора`.
- `Novus` / `NOVUS`.
- `Мегамаркет`.
- `Eva`.
- `Good Food`.
- `Сільпо`.
- ТРЦ `Наше Небо`.
- ТРЦ `Respublika` / `Республіка`.
- Точки выдачи `Rozetka`.
- Точки выдачи `Епіцентр`.
- Отделения `Нова пошта`.
- Отделения `Justin`.
- Отделения `Укрпошта`.
- Ремонт техники Apple.
- Автомойки, СТО.
- Рынок `Столичный`.
- `Епіцентр`.
- `Metro`.

### Restaurants and cafes

- McDonald's.
- Sonado.
- `Золотий дуб`.
- Banana Cake.
- Not only Pizza.
- Flame.
- Moray Club.
- Did Madrid.
- Osama Sushi.
- Dominos.

## Bomb shelter / укриття

- В источнике указано наличие укрытия.
- Перечисленные элементы укрытия:
  - надежные входные двери;
  - вентиляционные системы;
  - запас воды;
  - основные средства первой необходимости;
  - места для отдыха;
  - световая вывеска для ориентации в темное время;
  - отопление;
  - освещение при отсутствии электроэнергии;
  - Wi-Fi-зона.
- Эти характеристики требуют подтверждения перед production use, особенно состояние готовности и доступность для жильцов.

## Parking

- Наземные парковочные места по внешнему периметру двора.
- В блоке коммерческих помещений упоминается большая парковочная зона.
- Количество мест, условия покупки/аренды и доступность не указаны.

## Commercial premises

- Коммерческие помещения предусмотрены на первых этажах.
- Адрес коммерческих помещений: Крюковщина, ул. Одесская, 23.
- В источнике указаны фасадные помещения в жилом комплексе.
- Технические параметры из PDF:
  - большие фасадные окна;
  - 7 кВт электрической мощности с возможностью увеличения;
  - прямые договоры на электроснабжение;
  - потолки 3 метра;
  - удобные входы и подъезды для клиентов;
  - большая парковочная зона.
- В источнике указано "20+ бизнесов выбрали эту локацию". Требует подтверждения перед production use.
- В источнике указано "более 2000 семей жителей" и "до 10 000 потенциального трафика вокруг". Требует подтверждения перед production use.

## Purchase programs mentioned in source

These are not stable facts for production answers without manager confirmation:

- Полная оплата.
- Рассрочка / розтермінування.
- єОселя для льготных категорий 3%.
- єОселя 7%.
- Альтернатива єОселі через ПриватБанк.
- Программа ПриватБанка `Житло в кредит`.
- Жилищные ваучеры до 2 000 000 грн.

## Requires confirmation before production use

Confirm with Orange Park manager before bot use:

- Current `tenant_id` and internal `business_id` in Alpstein AI.
- Current official `business_external_id`.
- Current sales office/contact channels and working hours.
- Whether the exact distance to metro Теремки should be stated as 6.5 км, 7 км, or another current value.
- Current active apartment inventory by room count, building, floor, area, and readiness.
- Current prices per m2 and total apartment prices.
- Current discounts, promotions, and deadlines.
- Current installment terms for each apartment type.
- Whether full-payment discount is 2%, 10%, or another value.
- Current єОселя terms and eligibility.
- Current PrivatBank credit terms and whether pre-approval in 2 minutes can be promised.
- Current housing voucher terms and limit.
- Current commercial premises inventory, price, traffic claims, and electricity capacity.
- Current number of built, actively building, and planned buildings.
- Current readiness/commissioning status of buildings.
- Current availability and condition of bomb shelter / укриття.
- Elevator brand: Schindler or Ozbesler.
- Whether smart-hall features are present in all sections or only selected sections.
- Whether mobile app access, license plate recognition, post lockers, WC, ramps, and stroller zones are present in all entrances.
- Whether `private primary school will be built` can be mentioned, and with what status/date.
- Whether warm floors and remote boiler control apply to all apartments or selected sections only.

## Time-sensitive or unstable data

Do not use without fresh manager confirmation:

- Active discount: 10% for 100% payment.
- Active discount: 10% on 3-room apartments under єОселя.
- Earlier source line: 2% discount for full payment.
- Price from 22,100 грн/м2.
- Pricing table:
  - 1-room 35-41 м2: 56,000-62,000 грн/м2;
  - 2-room 56-64 м2: 53,000-56,000 грн/м2;
  - 3-room two-level 95 м2: 39,983-40,843 грн/м2;
  - 4-room two-level 84-110 м2: 39,000-41,000 грн/м2.
- Construction status: 3 buildings actively under construction, 19 built, 16 planned.
- 0% installment for 12 months on selected 2-room apartments.
- 50% first payment for the 59.3 м2 ready 2-room apartment offer.
- Claim: only 3 such 2-room apartments left.
- Claim: only 4 apartments left in a building for the 3-room discount promotion.
- Claim: buildings already commissioned and renovation can start immediately after deal registration.
- PrivatBank credit terms:
  - up to 5,000,000 грн;
  - up to 20 years;
  - first payment from 30%;
  - 17.5% in the first year;
  - preliminary decision in 2 minutes.
- єОселя 3% / 7% terms.
- Housing vouchers up to 2,000,000 грн.

## AI usage constraints

- Do not invent prices.
- Do not invent apartment availability.
- Do not invent active promotions.
- Do not promise mortgage, єОселя, voucher, or bank approval.
- Do not guarantee booking, purchase approval, or exact monthly payment.
- If a customer asks for price, availability, discount, payment schedule, credit, voucher, or єОселя eligibility, collect contact details and hand off to a manager or say that the manager will confirm current terms.
- Do not use marketing claims as facts.
- Do not treat PDF promotional language as legally binding.
