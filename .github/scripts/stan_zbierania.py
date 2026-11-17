"""Stan zbierania danych Traficar (uzywane przez GitHub Actions).

Liczy dlugosc ostatniej ciaglej serii odczytow (przerwy krotsze niz
PRZERWA_H godzin) i zapisuje wynik w podsumowaniu uruchomienia oraz
w zmiennej wyjsciowej 'koniec' (true, gdy seria jest dosc dluga).
"""
import os
import sqlite3
import sys
from datetime import datetime

PRZERWA_H = 6


def czasy_odczytow(baza):
    try:
        with sqlite3.connect(f"file:{baza}?mode=ro", uri=True) as conn:
            wiersze = conn.execute("SELECT DISTINCT czas FROM odczyty ORDER BY czas")
            return [datetime.fromisoformat(w[0]) for w in wiersze]
    except sqlite3.Error:
        return []


def ciagla_seria(czasy):
    """Zwraca (liczba odczytow, godziny) ostatniej ciaglej serii."""
    if not czasy:
        return 0, 0.0
    poczatek = len(czasy) - 1
    while poczatek > 0 and (czasy[poczatek] - czasy[poczatek - 1]).total_seconds() <= PRZERWA_H * 3600:
        poczatek -= 1
    godziny = (czasy[-1] - czasy[poczatek]).total_seconds() / 3600
    return len(czasy) - poczatek, godziny


def main():
    baza, wymagane = sys.argv[1], float(sys.argv[2])
    czasy = czasy_odczytow(baza)
    liczba, godziny = ciagla_seria(czasy)
    koniec = godziny >= wymagane
    tekst = (f"Odczytow w bazie: {len(czasy)}. Ciagla seria: {liczba} odczytow, "
             f"{godziny:.1f} h z wymaganych {wymagane:g} h.")
    if koniec:
        tekst += " Zbieranie zakonczone - przeplyw zostanie wylaczony."
    print(tekst)
    for zmienna, wpis in (("GITHUB_STEP_SUMMARY", tekst + "\n"),
                          ("GITHUB_OUTPUT", f"koniec={'true' if koniec else 'false'}\n")):
        if os.environ.get(zmienna):
            with open(os.environ[zmienna], "a", encoding="utf-8") as plik:
                plik.write(wpis)


if __name__ == "__main__":
    main()
