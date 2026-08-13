# 1300 Луғат — Сайти веб (Русӣ ба Тоҷикӣ)

Версияи веб-и боти "1300 Луғати Русӣ-Тоҷикӣ": 26 дарс, тести интихобӣ, пешрафти
шахсӣ, сертификати PDF, пардохти курс (расид + тасдиқи админ) ва панели админ —
ҳама дар сайт, бе бот.

## Хусусиятҳо

- Сабти ном / даромадан бо рақами телефон ва парол
- 26 дарс × 50 луғат, дарси 1 ройгон, боқимонда пас аз пардохт кушода мешавад
- Тести интихобии 4-вариантӣ (10 савол дар як дарс), пешрафт дар SQLite
- Сертификати PDF (бо алифбои тоҷикӣ, reportlab)
- Пардохт: корбар сурати расидро бор мекунад, админ тасдиқ/рад мекунад
- Панели админ: статистика, корбарон, тасдиқи пардохт, идоракунии луғатҳо, сертификатҳо
- Дизайни рангин/бозигонаӣ (Baloo 2 + Nunito, "medallion" progress ring, lesson path)

## Насб

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Танзимот (ихтиёрӣ)

Тавассути environment variables метавонед инҳоро тағир диҳед:

```bash
export SECRET_KEY="таъиноти-махфии-худ"
export PAYMENT_CARD_NUMBER="9730 1552 2xxx xxxx"
export PAYMENT_CARD_NAME="Ному насаби соҳиби корт"
export COURSE_PRICE="89"
```

## Оғоз кардан

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Ҳангоми аввалин оғоз, база ва луғатҳо (аз `data/words.json`) худкор сохта мешаванд,
ва як админи пешфарз сохта мешавад:

- **Телефон:** `admin`
- **Парол:** `admin123`

⚠️ **Ин паролро ҳатман пас аз аввалин даромадан иваз кунед** (ҳозир UI барои
тағйири парол нест — метавонед бевосита дар SQLite `database/app.db` ҷадвали
`users` тағйир диҳед, ё скрипти хурди Python нависед).

## Сохтори лоиҳа

```
main.py                # Роутҳои асосӣ (auth, дарсҳо, тест API, профил, пардохт)
routers/admin.py       # Панели админ
config.py              # Танзимот
database/
  models.py            # SQL schema
  db.py                # Пайвастшавии SQLite + сидинги луғатҳо
services/
  auth_service.py       # Парол (PBKDF2), сабти ном, даромадан
  lesson_service.py      # Дарсҳо, пешрафт
  test_service.py         # Мантиқи тест (session-backed, аз нав сар шудан бехатар)
  certificate_service.py   # Сохтани сертификати PDF
  payment_service.py        # Расид, тасдиқ/рад
templates/             # Jinja2 (дизайни рангин)
static/css/style.css    # Тамоми дизайн-система
static/js та test.html   # JS-и тести AJAX-и
data/words.json         # 1300 луғат (ҳамон манбаи бот)
fonts/                  # DejaVu Sans (барои PDF-и кириллӣ)
```

## Депло (Railway / Render)

1. Лоиҳаро ба репозиторияи Git гузоред.
2. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. `SECRET_KEY`-ро дар environment variables-и сервис таъин кунед.
4. SQLite-ро дар volume-и доимӣ нигоҳ доред (масалан Railway volume), вагарна
   баъди ҳар деплой маълумот гум мешавад.

## Нуктаҳои техникӣ

- Ҳамон мантиқи бот (жетонҳои тест, пешгирии duplicate-click, parameterized SQL)
  ба веб кӯчонида шудааст, аммо ба ҷои aiosqlite/async — SQLite синхронӣ бо
  connection-per-thread истифода мешавад (мувофиқи threadpool-и FastAPI).
- Сессия тавассути cookie-и имзошуда (`SessionMiddleware`) идора мешавад — DB-и
  алоҳида барои сессия лозим нест.
- Расидҳои пардохт дар `static/uploads/receipts/` нигоҳ дошта мешаванд.
