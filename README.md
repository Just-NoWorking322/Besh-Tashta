"""Проект: Беш-Ташта

>----- Ориентир -----<

Management:
- accounts (кошельки/счета пользователя)
- categories (категории доходов и расходов)
- transactions (история операций: INCOME / EXPENSE)
- debts (долги: мне должны / я должен)
- close debt -> creates transaction (закрытие долга создаёт запись в истории операций)
- dashboard (общая сводка: баланс, доход/расход, долги, последние операции)
- stats summary (income_total, expense_total, balance)
- stats by category (куда тратились деньги / откуда приходили по категориям)
- filters:
  - transactions: type, account, category, q, from/to
  - debts: kind, is_closed, q, due_from/due_to

Users:
- custom user (email + phone_number + password)
- auth (JWT):
  - register
  - login (login = email or phone)
  - refresh
  - logout (blacklist refresh)
- profile:
  - me (GET/PATCH user + profile)
  - avatar, bio, date_of_birth
  - settings: notifications, theme, language
- privileges:
  - privileges list
  - buy privilege
  - my privileges
  - is_premium (если есть купленные привилегии)

Motivation:
- motivation items (контент карточек)
- types:
  - smart hints
  - financial tips
  - remember
  - quote of day
  - wish of day
- feed (лента по блокам)
- detail (подробнее по id)
- optional dynamic hints (например "мало средств")


>-- - -- -- Figma -- - -- -- <
https://www.figma.com/design/HodhFz2wvDMKnWUpoTElmY/Besh-Tashta?node-id=0-1&p=f&t=MUyufL45D6jUE3sG-0

>-- - -- -- Git Hub -- -- - --<
https://github.com/Just-NoWorking322/Besh-Tashta
"""