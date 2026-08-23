# Cardano NIGHT Redemption

Der aktuelle Cardano-Pfad besteht aus:

- `midnight_redeem_cardano.py`: validierende Kernlogik und interaktive CLI.
- `midnight_redeem_gui.py`: lokale Tkinter-GUI.
- `trezor_cardano_signer.py`: Hardware-Ableitung und Geraetesignatur.
- `requirements_cardano.txt`: benoetigte Python-Pakete.

Start:

```bash
python -m pip install -r cardano-claim/requirements_cardano.txt
python simple_gui.py
```

Die vollstaendige Bedienungs- und Sicherheitsbeschreibung steht in
[`../README_SIMPLE_GUI.md`](../README_SIMPLE_GUI.md).

Vor der Signatur validiert der aktuelle Pfad den offiziellen NIGHT Asset- und
Redemption-Script-Hash, Contract/Reference-UTxOs, Funding, Collateral samt
Return, ADA-Bilanz, Destination, Change und alle Transaktionsausgaenge.

Der aktuelle Pfad fragt keinen Seed und keine Passphrase am Computer ab. Der
Trezor liefert nur oeffentliche Adressen und signiert die gepruefte Plutus-
Transaktion nach physischer Freigabe. Bei aktivierter Passphrase wird die
Eingabe ausschliesslich auf dem Geraet angefordert; Host-Eingabe ist gesperrt.
Vor jeder weiteren Vorbereitung muss die abgeleitete Wallet die vollstaendige
Midnight-Zieladresse exakt enthalten. Der Trezor zeigt diese Zieladresse danach
zur physischen Bestaetigung an. Eine vertippte Passphrase kann deshalb nicht als
leere Wallet bis zum Transaktionsaufbau weiterlaufen.

## Historische Datei

`midnight_claim_cardano.py` ist ein alter Key-Export-Helfer aus der Claim-Phase.
Er baut, signiert und sendet keine aktuelle Redemption-Transaktion. Er wird von
den Launchern nicht mehr aufgerufen und soll fuer NIGHT Redemption nicht
verwendet werden.
