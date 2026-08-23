# MidnightClaimer

MidnightClaimer ist ein lokaler Cardano-Redemption-Client fuer bereits
geclaimte, aufgetaute NIGHT. Er verwendet die oeffentlichen Build-/Submit-
Endpunkte des offiziellen Redemption-Portals und signiert ueber die offizielle
Trezor-Bibliothek. Dabei zeigt er konkrete Backendfehler und prueft die komplette
unsigned Transaction vor der Signatur.

## Cardano Redemption starten

```bash
python -m pip install -r cardano-claim/requirements_cardano.txt
python simple_gui.py
```

Unter Windows startet `START_GUI.bat` dieselbe GUI. Eine ausfuehrliche Anleitung
steht in [README_SIMPLE_GUI.md](README_SIMPLE_GUI.md).

## Sicherheitsmodell

- Die GUI akzeptiert weder Seed Phrase noch Passphrase oder private Keys.
- Seed und Keys bleiben auf dem Trezor; eine Wallet-Passphrase wird nur auf dem
  Geraet eingegeben.
- Die App verweigert Host-Eingabe fuer Passphrase und PIN und erzeugt keine
  `.skey`-, `.vkey`- oder `.env`-Dateien.
- Vor dem Signieren werden Destination, NIGHT Asset und Betrag, offizieller
  Redemption-Script-Hash, Funding, Collateral-Return, Change und unerwartete
  Operationen geprueft.
- Die Einreichung benoetigt eine separate menschliche Bestaetigung.
- Der Trezor-Body-Hash wird gegen die unveraenderten CBOR-Body-Bytes geprueft;
  jede Witness-Signatur wird vor Submit lokal kryptografisch verifiziert.
- Jeder Signaturauftrag ist einmalig; Abbruch oder Fehler erfordern eine neue
  Vorbereitung aus aktuellem Chain-Zustand.

## Verzeichnisuebersicht

```text
cardano-claim/
  midnight_redeem_cardano.py   Kernlogik und CLI
  midnight_redeem_gui.py       interne Tkinter-Oberflaeche
  trezor_cardano_signer.py     Hardware-Ableitung und Geraetesignatur
  requirements_cardano.txt
bitcoin-claim/                  historische Claim-Key-Helfer
simple_gui.py                   Anwendungsstart der aktuellen GUI
tests/                          Offline-Regressionstests
```

Die historischen Claim-Key-Helfer sind nicht der aktuelle NIGHT-Redemption-Pfad
und werden von den GUI-Launchern nicht mehr gestartet.

Sie bleiben fuer ihren urspruenglichen, separaten Zweck dokumentiert:

- [Historischer Cardano-Key-Export](cardano-claim/README_CARDANO.md)
- [Historischer Bitcoin-Claim-Helfer](bitcoin-claim/README_BITCOIN.md)

Diese alten Helfer exportieren Schluesselmaterial und haben nicht das oben
beschriebene Hardware-Sicherheitsmodell. Fuer die aktuelle Cardano-Redemption
deshalb ausschliesslich `simple_gui.py` beziehungsweise `START_GUI.bat` nutzen.

## Tests

```bash
python -m pytest tests -q
```

Die Tests verwenden synthetische und bereits bestaetigte oeffentliche
Transaktionen; sie reichen keine Blockchain-Transaktion ein.
