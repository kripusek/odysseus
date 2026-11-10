# Dostęp zdalny — konfiguracja tej instalacji

Przygotowano adres `https://ai.kripusek.top` z Cloudflare Access ograniczonym
do konta właściciela. Tunel działa na komputerze z Odysseusem i przekazuje ruch
do `127.0.0.1:17011`; oryginalny tunel serwera i inne trasy nie były zmieniane.
Bez sesji Cloudflare adres przekierowuje na logowanie Access.

Do korzystania komputer musi być włączony, a aplikacja i model uruchomione.
`START.cmd` uruchamia interfejs, `MODEL-KRIPAI.cmd` opcjonalny lokalny serwer
modelu; szczegóły w `README-WINDOWS-KRIPUSEK.md`. Program tunelu znajduje się
w `%LOCALAPPDATA%\Odysseus-kripusek-runtime`, a jego token w osobnym prywatnym
katalogu `%LOCALAPPDATA%\Odysseus-kripusek-private`. Po restarcie komputera,
jeśli tunel nie działa, można uruchomić `TUNEL.cmd` i pozostawić jego okno.
Nie umieszczaj pliku tokenu w repozytorium i nie wysyłaj go w rozmowie.

Potwierdzono: tunel online oraz przekierowanie niezalogowanego klienta do
Cloudflare Access. Nie potwierdzono jeszcze zalogowanego czatu z Internetu ani
kompatybilności aplikacji Android z logowaniem Access. Cloudflare pośredniczy
w ruchu HTTPS; nie jest to lokalne szyfrowanie końcowe treści między telefonem
a komputerem. Wyłączenie komputera lub tunelu przerywa dostęp zdalny.
