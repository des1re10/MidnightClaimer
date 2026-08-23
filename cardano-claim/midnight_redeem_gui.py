#!/usr/bin/env python3
"""Tkinter front end for the verified Cardano NIGHT redemption workflow."""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
import traceback
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

from midnight_redeem_cardano import (
    DEFAULT_SCAN_LIMIT,
    MAX_SCAN_LIMIT,
    PreparedRedemption,
    RedemptionError,
    RedemptionWorkflow,
    SubmissionResult,
)


DERIVATION_LABELS = {
    "Aktuell / Icarus (Standard)": "icarus",
    "Historisch / Trezor 24 Woerter": "icarus_trezor",
}


class MidnightRedeemGui:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("MidnightClaimer - NIGHT einloesen")
        self.root.geometry("940x760")
        self.root.minsize(760, 640)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.workflow = RedemptionWorkflow()
        self.prepared: PreparedRedemption | None = None
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.busy = False
        self.worker: threading.Thread | None = None

        self._build_ui()
        self.root.after(100, self._drain_events)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        ttk.Label(
            main,
            text="NIGHT direkt einloesen",
            font=("Arial", 18, "bold"),
        ).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(
            main,
            text=(
                "Die App verwendet denselben Build-/Submit-Ablauf wie das offizielle "
                "Portal. Seed und private Schluessel bleiben auf dem Trezor; die "
                "Passphrase wird ausschliesslich auf dem Geraet eingegeben."
            ),
            wraplength=880,
            justify=tk.LEFT,
        ).grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(4, 14))

        form = ttk.LabelFrame(
            main, text="Destination und Trezor Hardware-Wallet", padding=14
        )
        form.grid(row=2, column=0, sticky=(tk.W, tk.E))
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Destination address:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10), pady=4
        )
        self.destination_entry = ttk.Entry(form)
        self.destination_entry.grid(row=0, column=1, columnspan=3, sticky=(tk.W, tk.E), pady=4)

        ttk.Label(form, text="Ableitung:").grid(
            row=1, column=0, sticky=tk.W, padx=(0, 10), pady=4
        )
        self.derivation_box = ttk.Combobox(
            form,
            state="readonly",
            values=list(DERIVATION_LABELS),
            width=32,
        )
        self.derivation_box.current(0)
        self.derivation_box.grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(form, text="Account Index:").grid(
            row=1, column=2, sticky=tk.E, padx=(20, 8), pady=4
        )
        self.account_spinbox = ttk.Spinbox(form, from_=0, to=100, width=6)
        self.account_spinbox.set("0")
        self.account_spinbox.grid(row=1, column=3, sticky=tk.W, pady=4)

        ttk.Label(form, text="Adressen je Rolle scannen:").grid(
            row=2, column=0, sticky=tk.W, padx=(0, 10), pady=4
        )
        self.scan_spinbox = ttk.Spinbox(
            form, from_=1, to=MAX_SCAN_LIMIT, width=6
        )
        self.scan_spinbox.set(str(DEFAULT_SCAN_LIMIT))
        self.scan_spinbox.grid(row=2, column=1, sticky=tk.W, pady=4)

        self.risk_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            form,
            variable=self.risk_var,
            text=(
                "Trezor Suite und Browser-Wallets sind geschlossen; ich pruefe "
                "Zieladresse, NIGHT-Betrag und Gebuehr vor der Geraetebestaetigung."
            ),
        ).grid(row=3, column=0, columnspan=4, sticky=tk.W, pady=(10, 4))

        actions = ttk.Frame(form)
        actions.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
        actions.columnconfigure(1, weight=1)
        self.prepare_button = ttk.Button(
            actions,
            text="1. Status laden und Transaktion pruefen",
            command=self.start_prepare,
        )
        self.prepare_button.grid(row=0, column=0, sticky=tk.W)
        self.submit_button = ttk.Button(
            actions,
            text="2. Gepruefte Transaktion signieren und senden",
            command=self.start_submit,
            state=tk.DISABLED,
        )
        self.submit_button.grid(row=0, column=2, sticky=tk.E)

        result_frame = ttk.LabelFrame(main, text="Pruefung und Ergebnis", padding=10)
        result_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(14, 0))
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)
        self.output = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Courier New", 10),
        )
        self.output.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.status_label = ttk.Label(main, text="Bereit.")
        self.status_label.grid(row=4, column=0, sticky=tk.W, pady=(8, 0))

    def start_prepare(self) -> None:
        if self.busy:
            return
        if not self.risk_var.get():
            messagebox.showwarning(
                "Bestaetigung erforderlich",
                "Bitte bestaetige zuerst den Sicherheitshinweis.",
            )
            return

        destination = self.destination_entry.get().strip()
        derivation_label = self.derivation_box.get()
        try:
            account_index = int(self.account_spinbox.get())
            scan_limit = int(self.scan_spinbox.get())
            derivation_type = DERIVATION_LABELS[derivation_label]
        except (KeyError, ValueError):
            messagebox.showerror(
                "Ungueltige Eingabe",
                "Account Index, Scan-Limit oder Ableitung ist ungueltig.",
            )
            return

        if self.prepared is not None:
            self.prepared = None
        self.submit_button.config(state=tk.DISABLED)
        self._set_busy(
            True,
            "Passphrase am Trezor eingeben und Zieladresse dort bestaetigen ...",
        )
        self._set_output(
            "Vorbereitung laeuft. Seed und Passphrase werden nicht am PC "
            "abgefragt. Nach der Passphrase zeigt der Trezor die vollstaendige "
            "Midnight-Zieladresse. Nur diese Adresse bestaetigen. Es wird noch "
            "nichts signiert oder gesendet.\n"
        )

        self.worker = threading.Thread(
            target=self._prepare_worker,
            args=(
                destination,
                account_index,
                scan_limit,
                derivation_type,
            ),
            daemon=False,
        )
        self.worker.start()

    def _prepare_worker(
        self,
        destination: str,
        account_index: int,
        scan_limit: int,
        derivation_type: str,
    ) -> None:
        try:
            prepared = self.workflow.prepare(
                destination_address=destination,
                account_index=account_index,
                scan_limit=scan_limit,
                derivation_type=derivation_type,
            )
        except (KeyError, RedemptionError) as exc:
            self.events.put(("prepare_error", str(exc)))
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            # Thread boundary: unexpected failures must reach the user instead of
            # disappearing in a background-thread traceback. Do not render the
            # exception text because preparation exceptions could contain input.
            _report_unexpected_thread_failure(exc)
            self.events.put(("prepare_error", _unexpected_error_text(exc)))
        else:
            self.events.put(("prepared", prepared))

    def start_submit(self) -> None:
        if self.busy or self.prepared is None:
            return
        prepared = self.prepared
        try:
            account_index = int(self.account_spinbox.get())
            scan_limit = int(self.scan_spinbox.get())
            derivation_type = DERIVATION_LABELS[self.derivation_box.get()]
        except (KeyError, ValueError):
            messagebox.showerror(
                "Ungueltige Eingabe",
                "Account Index, Scan-Limit oder Ableitung ist ungueltig.",
            )
            return
        if (
            self.destination_entry.get().strip() != prepared.destination_address
            or account_index != prepared.account_index
            or scan_limit != prepared.scan_limit
            or derivation_type != prepared.derivation_type
        ):
            self.prepared = None
            self.submit_button.config(state=tk.DISABLED)
            messagebox.showwarning(
                "Vorschau veraltet",
                "Destination oder Trezor-Einstellungen wurden nach der Pruefung "
                "geaendert. Bitte die Transaktion neu vorbereiten.",
            )
            return
        approved = messagebox.askyesno(
            "Verbindliche Freigabe",
            (
                "Die oben angezeigte Transaktion wird jetzt mit Payment-"
                "Schluesseln im Trezor signiert. Passphrase und Freigabe "
                "erfolgen auf dem Geraet. Fortfahren?"
            ),
            icon=messagebox.WARNING,
        )
        if not approved:
            return
        self._set_busy(
            True,
            "Auf dem Trezor pruefen und bestaetigen; danach wird eingereicht ...",
        )
        self.submit_button.config(state=tk.DISABLED)
        # The prepared request is one-shot. Remove it from the UI before any USB
        # interaction so a cancellation or uncertain result cannot be retried.
        self.prepared = None
        self.worker = threading.Thread(
            target=self._submit_worker,
            args=(prepared,),
            daemon=False,
        )
        self.worker.start()

    def _submit_worker(self, prepared: PreparedRedemption) -> None:
        try:
            result = self.workflow.submit(prepared)
        except (KeyError, RedemptionError) as exc:
            self.events.put(("submit_error", str(exc)))
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            # Keep raw provider payloads out of the UI on unexpected failures.
            _report_unexpected_thread_failure(exc)
            self.events.put(("submit_error", _unexpected_error_text(exc)))
        else:
            self.events.put(("submitted", result))

    def _drain_events(self) -> None:
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            self.worker = None
            if event == "prepared":
                if not isinstance(payload, PreparedRedemption):
                    raise RuntimeError("Prepared event has an invalid payload")
                self.prepared = payload
                self._set_output(
                    f"SIGNATUR: {payload.signing_method}\n"
                    "SEED/PASSPHRASE AUF DEM PC: NEIN\n\n"
                    f"{payload.preview.to_text()}"
                )
                self._set_busy(False, "Transaktion geprueft. Bitte Vorschau kontrollieren.")
                self.submit_button.config(state=tk.NORMAL)
            elif event == "prepare_error":
                self._set_output(f"VORBEREITUNG FEHLGESCHLAGEN\n\n{payload}")
                self._set_busy(False, "Nicht signiert, nicht gesendet.")
            elif event == "submitted":
                if not isinstance(payload, SubmissionResult):
                    raise RuntimeError("Submitted event has an invalid payload")
                self._append_output(
                    "\n\nEINGEREICHT\n"
                    f"Transaction ID: {payload.transaction_id}\n"
                    "Geschaetzte Bearbeitungszeit: "
                    f"{payload.estimated_submission_time} Sekunden\n"
                )
                self._set_busy(False, "Redemption wurde eingereicht.")
                messagebox.showinfo(
                    "Eingereicht",
                    f"Midnight Transaction ID:\n{payload.transaction_id}",
                )
            elif event == "submit_error":
                self._append_output(f"\n\nEINREICHUNG FEHLGESCHLAGEN\n\n{payload}")
                self._set_busy(False, "Signaturauftrag verbraucht; bitte neu vorbereiten.")
        self.root.after(100, self._drain_events)

    def _set_busy(self, busy: bool, status: str) -> None:
        self.busy = busy
        self.status_label.config(text=status)
        self.prepare_button.config(state=tk.DISABLED if busy else tk.NORMAL)

    def _set_output(self, text: str) -> None:
        self.output.config(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, text)
        self.output.config(state=tk.DISABLED)

    def _append_output(self, text: str) -> None:
        self.output.config(state=tk.NORMAL)
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.config(state=tk.DISABLED)

    def close(self) -> None:
        if self.busy:
            messagebox.showwarning(
                "Vorgang laeuft",
                "Bitte den laufenden Vorgang am Trezor abschliessen oder ablehnen "
                "und danach das Fenster schliessen.",
            )
            return
        self.prepared = None
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def _report_unexpected_thread_failure(exc: Exception) -> None:
    print(
        f"Unexpected MidnightClaimer worker failure: {type(exc).__name__}",
        file=sys.stderr,
    )
    traceback.print_tb(exc.__traceback__, file=sys.stderr)


def _unexpected_error_text(exc: Exception) -> str:
    return f"Unerwarteter Fehler: {type(exc).__name__}"


def main() -> None:
    MidnightRedeemGui().run()


if __name__ == "__main__":
    main()
