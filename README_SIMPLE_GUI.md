# MidnightClaimer GUI: Cardano NIGHT Redemption

Die GUI loest bereits geclaimte und aufgetaute NIGHT direkt ein. Sie bildet den
aktuellen Ablauf des offiziellen Redemption-Portals lokal nach und zeigt
konkrete API-Fehler statt nur `Something went wrong`.

## Sicherheitsmodell

Die aktuelle GUI besitzt absichtlich keine Eingabefelder fuer Seed Phrase,
Passphrase oder private Schluessel. Seed und private Keys verlassen den Trezor
nicht. Bei einer Passphrase-Wallet fordert die App ausschliesslich die Eingabe
auf dem Trezor an und verweigert eine Passphrase- oder PIN-Eingabe am Computer.

Der Rechner sieht nur oeffentliche Adressen und die vom Trezor zurueckgegebene
Signatur. Vor dem Submit prueft die App zusaetzlich den Body Hash, den Public-Key-
Hash und die Signatur lokal. Eine absolute Garantie gegen manipulierte Firmware,
einen kompromittierten Rechner oder Bedienfehler gibt es trotzdem nicht. Deshalb
muessen Zieladresse, NIGHT-Betrag, Gebuehr und Collateral sowohl in der Vorschau
als auch auf dem Trezor kontrolliert werden.

Eine falsche Passphrase erzeugt auf dem Trezor ohne Fehlermeldung eine andere
Wallet. Deshalb setzt die App die Vorbereitung nur fort, wenn diese Wallet die
vollstaendige Midnight-Zieladresse im gewaehlten Account und Scan-Bereich exakt
ableitet. Der Trezor zeigt anschliessend genau diese Zieladresse zur physischen
Bestaetigung an. Die Passphrase selbst wird dabei weder angezeigt noch an den
Computer uebertragen.

## Installation und Start

Voraussetzung ist Python 3.10 oder neuer.

Vor dem Start Trezor Suite, Lace, Typhon und andere Programme schliessen, die
auf den Trezor zugreifen. Trezor verbinden, entsperren und aktuelle offizielle
Firmware verwenden.

```bash
python -m pip install -r cardano-claim/requirements_cardano.txt
```

Unter Windows danach `START_GUI.bat` doppelklicken. Unter Linux/macOS:

```bash
./run_simple_gui.sh
```

Alternativ kann der gleiche Ablauf ohne GUI gestartet werden:

```bash
python cardano-claim/midnight_redeem_cardano.py
```

## Eingaben

- `Destination address`: die vollstaendige `addr1...`-Adresse aus dem
  Midnight-Portal. NIGHT wird immer an diese Adresse ausgegeben.
- `Ableitung`: normalerweise `Aktuell / Icarus`. Fuer ein historisch angelegtes
  Cardano-Konto mit 24-Wort-Trezor-Seed kann
  `Historisch / Trezor 24 Woerter` erforderlich sein.
- `Account Index`: Trezor Suite `Account #1` entspricht Index `0`.
- `Adressen je Rolle scannen`: Standard ist 20 externe und 20 interne
  Adressen. Wenn dort keine ausreichenden UTxOs gefunden werden, den Wert bis
  maximal 100 erhoehen.

## Ablauf

1. Der Trezor liefert die oeffentlichen Cardano-Adressen. Die App sucht darin die
   vollstaendige Midnight-Zieladresse. Ohne exakten Treffer bricht sie ab. Bei
   einem Treffer zeigt der Trezor genau diese Zieladresse zur Bestaetigung an.
2. Koios liefert die oeffentlichen UTxOs dieser Adressen.
3. Die App verwendet ausschliesslich reine ADA-UTxOs ohne Token, Datum oder
   Reference Script. Sie waehlt den kleinsten ausreichenden Satz mit mindestens
   4,5 ADA in hoechstens drei Funding-Inputs.
4. Midnight liefert die unsigned Redemption-Transaktion.
5. Vor der Freigabe prueft die App:
   - Cardano Mainnet und vollstaendige Destination address,
   - offiziellen NIGHT Policy ID und Asset Name,
   - exakt sechs NIGHT-Dezimalstellen und den Betrag aus dem Thaw-Schedule,
   - offiziellen Redemption-Script-Hash, Contract- und Reference-Input,
   - Funding-, Collateral-Inputs und exakten Collateral-Return,
   - Gebuehr und moeglichen Collateral-Verlust mit je 5 ADA Obergrenze,
   - Change-Adresse sowie unerwartete Outputs, Minting, Withdrawals,
     Zertifikate und Governance-Aktionen.
6. Erst nach der zweiten, ausdruecklichen Bestaetigung wird die komplette
   Plutus-Transaktion an den Trezor gestreamt. Der Trezor zeigt die Signatur-
   details und erzeugt nach physischer Freigabe nur die Payment-Witnesses.
7. Die App berechnet die Transaction-ID direkt aus den unveraenderten CBOR-
   Body-Bytes. Sie akzeptiert die Witnesses nur, wenn Trezor-Body-Hash, Public-
   Key-Hash und Ed25519-Signatur lokal exakt dazu passen. Erst dann wird an
   Midnight gesendet.
8. Ein Signaturauftrag kann nur einmal verwendet werden. Nach Abbruch, Fehler
   oder unklarem Ergebnis muss aus frischem Chain-Zustand neu vorbereitet werden.

NIGHT geht nicht an eine neu erzeugte Wallet und auch nicht an die
Change-Adresse. Das Protokoll gibt NIGHT immer an die urspruengliche Destination
address aus; die abgeleitete interne Adresse erhaelt nur ADA-Change.

## Welche Daten verlassen den Rechner?

- Koios: abgeleitete oeffentliche Cardano-Adressen.
- Midnight beim Build: Destination address, Change-Adresse und CBOR der
  ausgewaehlten oeffentlichen UTxOs.
- Koios nach dem Build: die oeffentlichen Contract- und Reference-UTxO-IDs aus
  der unsigned Transaction.
- Midnight beim Submit: unsigned Transaction und Payment-Witness-Set.

Seed Phrase, Passphrase, PIN und private Keys gelangen nicht in die App und werden
nicht uebertragen. Die Passphrase wird bei Vorbereitung und Signatur jeweils
direkt auf dem Trezor eingegeben.

## Fehlerbilder

Die GUI zeigt `type`, `message` und `info` des Backends an. Beispiele:

- `no_redeemable_thaws`: Das Backend sieht aktuell keinen einloesbaren Thaw;
  das ist kein Trezor- oder ADA-Fehler.
- `No Trezor device found` oder `DeviceIsBusy`: Trezor Suite und Browser-Wallets
  vollstaendig schliessen, Trezor neu verbinden und erneut vorbereiten.
- `cannot accept the passphrase on-device`: Dieses Modell bietet keine sichere
  Geraeteeingabe. Die App faellt absichtlich nicht auf Host-Eingabe zurueck.
- `passphrase wallet ... does not match`: Bei der zweiten Geraeteeingabe wurde
  eine andere Passphrase verwendet. Nichts wurde gesendet; neu vorbereiten.
- `Passphrase-Wallet passt nicht zur Midnight-Zieladresse`: Die eingegebene
  Passphrase, Ableitung, der Account Index oder der Scan-Bereich gehoert nicht
  zur Portal-Zieladresse. Nichts wurde signiert oder gesendet.
- `missing_or_spent_inputs`: Ein ausgewaehlter UTxO wurde zwischen Abfrage und
  Build ausgegeben. Neu vorbereiten.
- `No sufficient pure-ADA UTxOs`: Genug Gesamt-ADA kann vorhanden sein, aber
  nicht auf einer gescannten, tokenfreien UTxO. Scan-Limit erhoehen oder in
  Trezor Suite einen reinen ADA-UTxO auf eine eigene Adresse erzeugen.
- `Transaction must contain exactly one destination output`: Die Transaktion
  wird absichtlich nicht signiert; dies ist eine harte Sicherheitspruefung.
- `Submission status is uncertain`: Nicht sofort erneut senden. Zuerst die in
  der Vorschau angezeigte Transaction ID im Explorer pruefen.

Automatisierte Tests signieren und senden keine Mainnet-Transaktion.
