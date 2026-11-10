# Odysseus — uruchomienie w Windows

To osobna kopia Odysseus, na licencji AGPL-3.0-or-later. Szczegóły licencji i zależności są w `LICENSE` i `ACKNOWLEDGMENTS.md`.

## Windows / PowerShell

Uruchom `START.cmd` dwuklikiem albo w PowerShell:

```powershell
.\START.cmd
```

Otwórz `http://127.0.0.1:17011`. Program nasłuchuje tylko lokalnie, z włączonym logowaniem. Dane są w `%LOCALAPPDATA%\Odysseus-kripusek-data`; środowisko Python `venv` znajduje się w katalogu programu. Pierwszy start pobiera zależności i uruchamia konfigurację konta administratora. Wpisz hasło lokalnie, nie umieszczaj go w plikach projektu ani nie wysyłaj w rozmowie. Ponowny start zachowuje istniejące konto i dane. Zatrzymaj program przez Ctrl+C w jego oknie. Launcher pochodzi z projektu Odysseus, a jego komunikaty są po angielsku.

## Lokalny model

Odysseus nie uruchamia przez ten plik modelu ani nie przełącza trybu GPU KripAI. Aby użyć modelu, uruchom osobno zaufany lokalny serwer zgodny z OpenAI API, dostępny na loopback. W ustawieniach administracyjnych Odysseus, w sekcji usług i endpointów modeli, dodaj endpoint z adresem serwera zakończonym `/v1`, a jeśli serwer wymaga uwierzytelnienia, wprowadź jego klucz lokalnie w formularzu. Odśwież listę modeli i wybierz model w czacie. Port i klucz zależą od konfiguracji tego serwera; nie wpisuj klucza do README, skryptów ani repozytorium. Ustawienia endpointu mogą być zapisane w prywatnych danych Odysseus.

Na tym komputerze sprawdzono osobny tymczasowy `llama-server.exe` CUDA z modelem Qwen3 8B Q4 oraz ograniczeniem do 12 warstw GPU: kod konektora Odysseus wykrył model i uzyskał poprawną odpowiedź na krótkie pytanie. Nie był to test pełnego czatu przez interfejs. Dostępna pamięć GPU i szybkość zależą od innych uruchomionych programów. Serwer modelu należy zakończyć osobno.

Dodatkowe informacje o konfiguracji i ograniczeniach znajdują się w `website/setup.md`. Funkcje takie jak zewnętrzne wyszukiwanie i niektóre integracje wymagają dodatkowej konfiguracji; nie zakładaj, że działają po samym uruchomieniu.

Potwierdzony test rzeczywistego czatu API z lokalnym modelem, logowaniem i
tymczasową bazą: [TESTY-WINDOWS-KRIPUSEK.md](TESTY-WINDOWS-KRIPUSEK.md).
