"""Monitor floty Traficar: odczyty dostepnych aut zapisywane w bazie SQLite."""

import argparse
import sqlite3
import time
from pathlib import Path

import requests

API = "https://fioletowe.live/api/v1"
STREFA = 1  # 1 = Krakow
BAZA = Path(__file__).resolve().parent / "dane" / "proba.db"

SQL_TABELE = """
CREATE TABLE IF NOT EXISTS modele (
    id          INTEGER PRIMARY KEY,
    nazwa       TEXT NOT NULL,
    typ         INTEGER,
    pojemnosc   REAL,
    elektryczny INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS auta (
    id          INTEGER PRIMARY KEY,
    model_id    INTEGER REFERENCES modele(id),
    rejestracja TEXT,
    nr_boczny   INTEGER
);
CREATE TABLE IF NOT EXISTS odczyty (
    czas    TEXT NOT NULL,
    auto_id INTEGER NOT NULL REFERENCES auta(id),
    lat     REAL,
    lng     REAL,
    adres   TEXT,
    paliwo  REAL,
    zasieg  INTEGER,
    PRIMARY KEY (czas, auto_id)
) WITHOUT ROWID;
"""


def utworz_tabele(baza):
    Path(baza).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(baza) as conn:
        conn.executescript(SQL_TABELE)


def pobierz(sciezka, **parametry):
    odpowiedz = requests.get(API + sciezka, params=parametry, timeout=30)
    odpowiedz.raise_for_status()
    return odpowiedz.json()


def pobierz_modele():
    return pobierz("/car-models")["carModels"]


def pobierz_auta(strefa=STREFA):
    """Zwraca slownik z kluczami 'cars' (lista aut) i 'lastUpdate' (czas serwera)."""
    return pobierz("/cars", zoneId=strefa)


def zapisz_modele(baza, modele):
    with sqlite3.connect(baza) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO modele VALUES (?, ?, ?, ?, ?)",
            [(m["id"], m["name"], m.get("type"), m.get("maxFuel"),
              int(bool(m.get("electric")))) for m in modele],
        )


def zapisz_odczyt(baza, dane):
    """Zapisuje jeden odczyt; zwraca liczbe nowych wierszy (0 = odczyt juz byl)."""
    czas = dane["lastUpdate"]
    with sqlite3.connect(baza) as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO auta VALUES (?, ?, ?, ?)",
            [(a["id"], a["modelId"], a["regPlate"], a["sideNumber"]) for a in dane["cars"]],
        )
        po_autach = conn.total_changes
        conn.executemany(
            "INSERT OR IGNORE INTO odczyty VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(czas, a["id"], float(a["lat"]), float(a["lng"]), a["location"],
              a["fuel"], a["range"]) for a in dane["cars"]],
        )
        return conn.total_changes - po_autach


def odczyt(baza=BAZA, strefa=STREFA):
    utworz_tabele(baza)
    zapisz_modele(baza, pobierz_modele())
    dane = pobierz_auta(strefa)
    nowe = zapisz_odczyt(baza, dane)
    print(f"{dane['lastUpdate']}: aut {len(dane['cars'])}, nowych wierszy {nowe}")
    return nowe


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baza", default=str(BAZA))
    parser.add_argument("--strefa", type=int, default=STREFA)
    parser.add_argument("--petla", type=float, metavar="MINUTY",
                        help="powtarzaj odczyt co podana liczbe minut")
    args = parser.parse_args(argv)
    odczyt(args.baza, args.strefa)
    if args.petla:
        import schedule
        schedule.every(args.petla).minutes.do(odczyt, args.baza, args.strefa)
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    main()
