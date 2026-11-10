# Test natywnego Odysseusa — Windows, 10.11.2026

Wykonano próbę w osobnym katalogu danych i tymczasowej bazie SQLite z kontem
testowym. Rzeczywisty backend uvicorn i osobny llama-server.exe korzystały z
lokalnego modelu Qwen3 8B Q4, CUDA i 12 warstw GPU. Dane prywatne KripAI nie
były zmieniane. Przed próbą sprawdzono brak CS2 i aktywnych zadań KripAI.

- Brak sesji: 401; konfiguracja konta: 200; złe hasło: 401; logowanie: 200.
- Dodanie lokalnego endpointu: 200; utworzenie sesji: 200; `/api/chat`: 200
  i niepusta odpowiedź rzeczywistego modelu; wylogowanie: 200; następny dostęp: 401.
- Procesy testowe zatrzymano, tymczasową bazę i plik klucza usunięto.

Próba dotyczy API, a nie wizualnego interfejsu przeglądarki. Użyto launchera
PowerShell z testowym katalogiem danych; docelowego START.cmd nie uruchamiano,
ponieważ wskazuje własny katalog użytkownika. Aplikacja Android oraz Cardputer
nie były częścią tej próby. Wcześniejszy test START.cmd używał atrapy PowerShell
i potwierdził tylko argumenty i zmienne środowiskowe.
