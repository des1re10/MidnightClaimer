#!/usr/bin/env python3
"""Redeem thawed NIGHT with a Trezor hardware signer.

This client follows the transaction flow used by the official redemption portal:

1. Read the thawing schedule from the Midnight API.
2. Read fee UTxOs from Koios.
3. Ask the Midnight API to build an unsigned redemption transaction.
4. Verify the complete transaction before asking for human approval.
5. Create only the Cardano payment-key witnesses and submit them.

The seed and private keys stay on the Trezor.  If the wallet uses a passphrase,
it is entered on-device and never enters this Python process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from io import BytesIO
from threading import Lock
from types import MappingProxyType
from typing import AbstractSet, Any, Iterable, Mapping, Sequence

import cbor2
import requests
from pycardano import (
    Address,
    AssetName,
    MultiAsset,
    Network,
    PyCardanoException,
    ScriptHash,
    Transaction,
    TransactionBody,
    TransactionId,
    TransactionInput,
    TransactionOutput,
    UTxO,
    Value,
    VerificationKeyHash,
)

from trezor_cardano_signer import (
    TrezorHardwareError,
    create_witness_set as create_trezor_witness_set,
    derive_base_addresses,
)


MIDNIGHT_API_BASE = "https://mainnet.prod.gd.midnighttge.io"
MIDNIGHT_PORTAL_ORIGIN = "https://redeem.midnight.gd"
KOIOS_API_BASE = "https://api.koios.rest/api/v1"

# REQUIRED FALLBACK: The public mainnet API rejects the default Python user
# agent while accepting the portal's ordinary browser headers (observed
# 2026-08-23). Removing these fixed, non-secret headers prevents build/submit;
# they do not change endpoint order or weaken transaction validation.
PORTAL_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": MIDNIGHT_PORTAL_ORIGIN,
    "Referer": f"{MIDNIGHT_PORTAL_ORIGIN}/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
}

NIGHT_POLICY_ID = ScriptHash(
    bytes.fromhex("0691b2fecca1ac4f53cb6dfb00b7013e561d1f34403b957cbb5af1fa")
)
NIGHT_ASSET_NAME = AssetName(bytes.fromhex("4e49474854"))
NIGHT_SUBUNITS_PER_TOKEN = 1_000_000
REDEMPTION_SCRIPT_HASH = ScriptHash(
    bytes.fromhex("5986bfcc0cbfc60dec8df87715cc95d03817aac386b0e9d33da03b39")
)

MIN_FUNDING_LOVELACE = 4_500_000
MAX_FUNDING_INPUTS = 3
MAX_ALLOWED_FEE_LOVELACE = 5_000_000
DEFAULT_SCAN_LIMIT = 20
MAX_SCAN_LIMIT = 100
KOIOS_ADDRESS_BATCH_SIZE = 25
HTTP_TIMEOUT_SECONDS = 45

REDEEMABLE_STATUSES = frozenset({"redeemable", "failed"})
IN_PROGRESS_STATUSES = frozenset({"queued", "submitted"})
REDEEMED_STATUSES = frozenset({"confirming", "confirmed"})
UPCOMING_STATUSES = frozenset({"upcoming"})
IGNORED_STATUSES = frozenset({"skipped"})
PORTAL_THAW_STATUSES = (
    REDEEMABLE_STATUSES
    | IN_PROGRESS_STATUSES
    | REDEEMED_STATUSES
    | UPCOMING_STATUSES
    | IGNORED_STATUSES
)
SUPPORTED_DERIVATION_TYPES = frozenset({"icarus", "icarus_trezor"})


class RedemptionError(RuntimeError):
    """Base error for an actionable redemption failure."""


class InputValidationError(RedemptionError):
    """Raised when user input violates a required invariant."""


class ApiError(RedemptionError):
    """A structured error returned by Midnight or Koios."""

    def __init__(
        self,
        service: str,
        status_code: int,
        error_type: str,
        message: str,
        info: str | None = None,
    ) -> None:
        details = f"{service} HTTP {status_code}: {error_type}: {message}"
        if info:
            details = f"{details} ({info})"
        super().__init__(details)
        self.service = service
        self.status_code = status_code
        self.error_type = error_type
        self.message = message
        self.info = info


class TransactionValidationError(RedemptionError):
    """Raised when an unsigned transaction is not safe to sign."""


@dataclass(frozen=True)
class Thaw:
    night_subunits: int
    status: str
    thawing_period_start: str
    transaction_id: str | None


@dataclass(frozen=True)
class ThawSchedule:
    thaws: tuple[Thaw, ...]

    def _sum_subunits(self, statuses: frozenset[str]) -> int:
        return sum(
            thaw.night_subunits for thaw in self.thaws if thaw.status in statuses
        )

    @property
    def redeemable_now(self) -> Decimal:
        return Decimal(self.redeemable_now_subunits) / NIGHT_SUBUNITS_PER_TOKEN

    @property
    def redeemable_now_subunits(self) -> int:
        return self._sum_subunits(REDEEMABLE_STATUSES)

    @property
    def redeemed(self) -> Decimal:
        return Decimal(self._sum_subunits(REDEEMED_STATUSES)) / NIGHT_SUBUNITS_PER_TOKEN

    @property
    def in_progress(self) -> Decimal:
        return Decimal(self._sum_subunits(IN_PROGRESS_STATUSES)) / NIGHT_SUBUNITS_PER_TOKEN

    @property
    def total_left_subunits(self) -> int:
        return self._sum_subunits(
            REDEEMABLE_STATUSES | IN_PROGRESS_STATUSES | UPCOMING_STATUSES
        )

    @property
    def continuation_night_subunits(self) -> int:
        return self._sum_subunits(UPCOMING_STATUSES)

    @property
    def total(self) -> Decimal:
        included = PORTAL_THAW_STATUSES - IGNORED_STATUSES
        return Decimal(self._sum_subunits(included)) / NIGHT_SUBUNITS_PER_TOKEN

    @property
    def expected_night_subunits(self) -> int:
        return self.redeemable_now_subunits


@dataclass(frozen=True)
class DerivedAddress:
    address: str
    derivation_path: str

    @property
    def payment_key_hash(self) -> VerificationKeyHash:
        try:
            payment_part = Address.from_primitive(self.address).payment_part
        except (PyCardanoException, TypeError, ValueError) as exc:
            raise InputValidationError(
                "A derived hardware address is malformed"
            ) from exc
        if not isinstance(payment_part, VerificationKeyHash):
            raise InputValidationError(
                "A derived hardware address has no payment-key credential"
            )
        return payment_part


@dataclass(frozen=True)
class FundingUtxo:
    reference: str
    address: str
    derivation_path: str
    lovelace: int
    cbor: str


@dataclass(frozen=True)
class NativeAssetAmount:
    policy_id: str
    asset_name: str
    quantity: int


@dataclass(frozen=True)
class ChainUtxo:
    reference: str
    address: str
    lovelace: int
    assets: tuple[NativeAssetAmount, ...]
    is_spent: bool
    has_datum_hash: bool
    has_inline_datum: bool
    has_reference_script: bool
    reference_script_hash: str | None
    reference_script_type: str | None


@dataclass(frozen=True)
class TransactionOutputPreview:
    address: str
    lovelace: int
    night_subunits: int
    has_datum: bool


@dataclass(frozen=True)
class RedemptionPreview:
    destination_address: str
    change_address: str
    redeemable_night: Decimal
    fee_ada: Decimal
    selected_funding_ada: Decimal
    total_collateral_ada: Decimal
    collateral_return_ada: Decimal
    selected_inputs: tuple[str, ...]
    collateral_inputs: tuple[str, ...]
    outputs: tuple[TransactionOutputPreview, ...]
    transaction_id: str

    def to_text(self) -> str:
        lines = [
            "UNSIGNIERTE REDEMPTION GEPRUEFT",
            f"Zieladresse: {self.destination_address}",
            f"NIGHT: {self.redeemable_night:f}",
            f"Gebuehr: {self.fee_ada:f} ADA",
            f"Ausgewaehlte Funding-UTxOs: {self.selected_funding_ada:f} ADA",
            f"Maximaler Collateral-Verlust bei Script-Fehler: "
            f"{self.total_collateral_ada:f} ADA",
            f"Collateral-Return an Change: {self.collateral_return_ada:f} ADA",
            f"Change-Adresse: {self.change_address}",
            f"Transaction-ID (Body Hash): {self.transaction_id}",
            "Funding Inputs:",
        ]
        lines.extend(f"  - {reference}" for reference in self.selected_inputs)
        lines.append("Collateral Inputs:")
        lines.extend(f"  - {reference}" for reference in self.collateral_inputs)
        lines.append("Outputs:")
        for output in self.outputs:
            night = Decimal(output.night_subunits) / NIGHT_SUBUNITS_PER_TOKEN
            ada = Decimal(output.lovelace) / 1_000_000
            lines.append(
                f"  - {output.address} | {ada:f} ADA | {night:f} NIGHT"
                f" | datum={output.has_datum}"
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class SubmissionResult:
    transaction_id: str
    estimated_submission_time: int


@dataclass(frozen=True)
class PreparedRedemption:
    destination_address: str
    transaction_cbor: str = field(repr=False)
    preview: RedemptionPreview
    signing_method: str
    account_index: int
    scan_limit: int
    derivation_type: str
    _reference_paths: Mapping[str, str] = field(repr=False, compare=False)
    _key_hash_by_path: Mapping[str, VerificationKeyHash] = field(
        repr=False, compare=False
    )
    _consumed: bool = field(default=False, init=False, repr=False, compare=False)
    _consume_lock: Lock = field(
        default_factory=Lock, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_reference_paths",
            MappingProxyType(dict(self._reference_paths)),
        )
        object.__setattr__(
            self,
            "_key_hash_by_path",
            MappingProxyType(dict(self._key_hash_by_path)),
        )

    def create_witness_set(self) -> str:
        """Ask the Trezor to sign this verified body exactly once."""
        with self._consume_lock:
            if self._consumed:
                raise RedemptionError(
                    "This signing request was already used; prepare the transaction again"
                )
            # Consume before USB interaction. A cancelled or uncertain signing attempt
            # must be rebuilt from fresh chain state instead of silently retried.
            object.__setattr__(self, "_consumed", True)

        body_hash = _exact_transaction_body_hash(self.transaction_cbor)
        if body_hash.hex() != self.preview.transaction_id:
            raise TransactionValidationError(
                "The prepared transaction changed after it was verified"
            )

        try:
            return create_trezor_witness_set(
                transaction_cbor=self.transaction_cbor,
                expected_transaction_id=self.preview.transaction_id,
                reference_paths=self._reference_paths,
                key_hash_by_path=self._key_hash_by_path,
                change_address=self.preview.change_address,
                account_index=self.account_index,
                derivation_type=self.derivation_type,
            )
        except TrezorHardwareError as exc:
            raise RedemptionError(str(exc)) from exc


class MidnightRedemptionClient:
    """Strict HTTP client for the public Midnight redemption endpoints."""

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session if session is not None else requests.Session()

    def get_schedule(self, destination_address: str) -> ThawSchedule:
        payload = self._request_json(
            "GET",
            f"{MIDNIGHT_API_BASE}/thaws/{destination_address}/schedule",
        )
        return parse_thaw_schedule(payload)

    def build_transaction(
        self,
        destination_address: str,
        change_address: str,
        funding_utxos: Sequence[FundingUtxo],
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            f"{MIDNIGHT_API_BASE}/thaws/{destination_address}/transactions/build",
            json_body={
                "change_address": change_address,
                "collateral_utxos": [],
                "funding_utxos": [utxo.cbor for utxo in funding_utxos],
            },
        )

    def submit_transaction(
        self,
        destination_address: str,
        transaction_cbor: str,
        witness_set_cbor: str,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            f"{MIDNIGHT_API_BASE}/thaws/{destination_address}/transactions",
            json_body={
                "transaction": transaction_cbor,
                "transaction_witness_set": witness_set_cbor,
            },
        )

    def get_transaction_status(
        self, destination_address: str, transaction_id: str
    ) -> Mapping[str, Any]:
        return self._request_json(
            "GET",
            (
                f"{MIDNIGHT_API_BASE}/thaws/{destination_address}"
                f"/transactions/{transaction_id}"
            ),
        )

    def _request_json(
        self,
        method: str,
        url: str,
        json_body: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        try:
            response = self._session.request(
                method,
                url,
                headers=PORTAL_HEADERS,
                json=json_body,
                timeout=HTTP_TIMEOUT_SECONDS,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise ApiError("Midnight", 0, "network_error", str(exc)) from exc

        payload = _decode_json_response(response, "Midnight")
        if response.status_code < 200 or response.status_code >= 300:
            raise _api_error_from_payload("Midnight", response.status_code, payload)
        if not isinstance(payload, Mapping):
            raise ApiError(
                "Midnight",
                response.status_code,
                "invalid_response",
                "Expected a JSON object",
            )
        return payload


class KoiosClient:
    """Read-only source for the fee wallet's public UTxOs."""

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session if session is not None else requests.Session()

    def get_address_utxos(self, addresses: Sequence[str]) -> tuple[ChainUtxo, ...]:
        if not addresses:
            raise InputValidationError("At least one derived address is required")

        result: list[ChainUtxo] = []
        for batch in _chunks(addresses, KOIOS_ADDRESS_BATCH_SIZE):
            result.extend(
                self._post_utxos(
                    "address_utxos",
                    {"_addresses": list(batch), "_extended": True},
                )
            )
        return tuple(result)

    def get_utxo_info(self, references: Sequence[str]) -> tuple[ChainUtxo, ...]:
        if not references:
            raise InputValidationError("At least one UTxO reference is required")
        return self._post_utxos(
            "utxo_info",
            {"_utxo_refs": list(references), "_extended": True},
        )

    def _post_utxos(
        self, endpoint: str, json_body: Mapping[str, Any]
    ) -> tuple[ChainUtxo, ...]:
        try:
            response = self._session.post(
                f"{KOIOS_API_BASE}/{endpoint}",
                headers={"Accept": "application/json"},
                json=json_body,
                timeout=HTTP_TIMEOUT_SECONDS,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise ApiError("Koios", 0, "network_error", str(exc)) from exc

        payload = _decode_json_response(response, "Koios")
        if response.status_code < 200 or response.status_code >= 300:
            raise _api_error_from_payload("Koios", response.status_code, payload)
        if not isinstance(payload, list):
            raise ApiError(
                "Koios",
                response.status_code,
                "invalid_response",
                "Expected a JSON array",
            )
        parsed = tuple(_parse_koios_utxo(item) for item in payload)
        references = [utxo.reference for utxo in parsed]
        if len(set(references)) != len(references):
            raise ApiError(
                "Koios",
                response.status_code,
                "invalid_response",
                "Duplicate UTxO reference",
            )
        return parsed


class RedemptionWorkflow:
    """End-to-end preparation and submission with a mandatory preview boundary."""

    def __init__(
        self,
        midnight_client: MidnightRedemptionClient | None = None,
        koios_client: KoiosClient | None = None,
    ) -> None:
        self.midnight_client = (
            midnight_client
            if midnight_client is not None
            else MidnightRedemptionClient()
        )
        self.koios_client = koios_client if koios_client is not None else KoiosClient()

    def prepare(
        self,
        destination_address: str,
        account_index: int = 0,
        scan_limit: int = DEFAULT_SCAN_LIMIT,
        derivation_type: str = "icarus",
    ) -> PreparedRedemption:
        """Prepare using only public addresses read from a connected Trezor."""
        destination = parse_mainnet_address(destination_address, "Destination address")
        schedule = self._load_redeemable_schedule(str(destination))
        try:
            snapshot = derive_base_addresses(
                account_index,
                scan_limit,
                derivation_type,
                verification_address=str(destination),
            )
        except TrezorHardwareError as exc:
            raise RedemptionError(str(exc)) from exc

        if snapshot.verified_destination.address != str(destination):
            raise TransactionValidationError(
                "Trezor wallet verification returned a different destination address"
            )

        derived_addresses = tuple(
            DerivedAddress(item.address, item.derivation_path)
            for item in snapshot.addresses
        )
        return self._prepare_from_addresses(
            destination,
            schedule,
            derived_addresses,
            account_index=account_index,
            scan_limit=scan_limit,
            derivation_type=derivation_type,
            signer_description=(
                f"Trezor Hardware: {snapshot.description}; Zieladresse bestaetigt "
                f"unter {snapshot.verified_destination.derivation_path}"
            ),
            verified_destination_path=(
                snapshot.verified_destination.derivation_path
            ),
        )

    def _load_redeemable_schedule(self, destination_address: str) -> ThawSchedule:
        schedule = self.midnight_client.get_schedule(destination_address)
        if schedule.in_progress > 0:
            raise TransactionValidationError(
                "A redemption is already queued or submitted for this address"
            )
        if schedule.redeemable_now_subunits <= 0:
            raise TransactionValidationError(
                "The Midnight API reports no NIGHT tranche as redeemable now"
            )
        return schedule

    def _prepare_from_addresses(
        self,
        destination: Address,
        schedule: ThawSchedule,
        derived_addresses: Sequence[DerivedAddress],
        *,
        account_index: int,
        scan_limit: int,
        derivation_type: str,
        signer_description: str,
        verified_destination_path: str,
    ) -> PreparedRedemption:
        address_by_text = {item.address: item for item in derived_addresses}
        destination_matches = tuple(
            item for item in derived_addresses if item.address == str(destination)
        )
        if len(destination_matches) != 1:
            raise TransactionValidationError(
                "The verified Midnight destination is not unique in the derived "
                "Trezor addresses"
            )
        if destination_matches[0].derivation_path != verified_destination_path:
            raise TransactionValidationError(
                "The verified Midnight destination path changed during preparation"
            )

        koios_utxos = self.koios_client.get_address_utxos(list(address_by_text))
        funding_utxos = build_funding_utxos(koios_utxos, address_by_text)
        try:
            selected_utxos = select_funding_utxos(funding_utxos)
        except TransactionValidationError as exc:
            raise TransactionValidationError(
                "Passphrase-Wallet kryptografisch gegen die Midnight-Zieladresse "
                f"bestaetigt ({verified_destination_path}). {exc}"
            ) from exc

        # The first internal address is deterministic and belongs to the same account.
        change_address = next(
            item.address
            for item in derived_addresses
            if item.derivation_path.endswith("/1/0")
        )
        build_result = self.midnight_client.build_transaction(
            str(destination),
            change_address,
            selected_utxos,
        )
        transaction_cbor = _required_string(build_result, "transaction")
        transaction = _decode_transaction(transaction_cbor)
        contract_reference, script_reference = _redemption_context_references(
            transaction, selected_utxos
        )
        context_utxos = self.koios_client.get_utxo_info(
            [contract_reference, script_reference]
        )
        context_by_reference = {utxo.reference: utxo for utxo in context_utxos}
        expected_context_references = {contract_reference, script_reference}
        if set(context_by_reference) != expected_context_references:
            missing = sorted(expected_context_references - set(context_by_reference))
            raise TransactionValidationError(
                f"Koios did not return the required redemption UTxOs: {missing}"
            )

        signer_owners = frozenset(
            item.payment_key_hash for item in derived_addresses
        )
        preview = validate_redemption_transaction(
            transaction_cbor=transaction_cbor,
            destination_address=str(destination),
            change_address=change_address,
            schedule=schedule,
            selected_utxos=selected_utxos,
            available_signer_key_hashes=signer_owners,
            context_utxos=context_by_reference,
        )

        return PreparedRedemption(
            destination_address=str(destination),
            transaction_cbor=transaction_cbor,
            preview=preview,
            signing_method=signer_description,
            account_index=account_index,
            scan_limit=scan_limit,
            derivation_type=derivation_type,
            _reference_paths={
                utxo.reference: utxo.derivation_path for utxo in selected_utxos
            },
            _key_hash_by_path={
                item.derivation_path: item.payment_key_hash
                for item in derived_addresses
            },
        )

    def submit(self, prepared: PreparedRedemption) -> SubmissionResult:
        witness_set = prepared.create_witness_set()
        try:
            payload = self.midnight_client.submit_transaction(
                prepared.destination_address,
                prepared.transaction_cbor,
                witness_set,
            )
        except ApiError as exc:
            if exc.status_code == 0 or exc.status_code >= 500:
                raise RedemptionError(
                    "Submission status is uncertain. Check transaction "
                    f"{prepared.preview.transaction_id} in an explorer before retrying"
                ) from exc
            raise
        try:
            transaction_id = _required_string(payload, "transaction_id")
            estimated_submission_time = _required_non_negative_int(
                payload, "estimated_submission_time"
            )
        except (KeyError, InputValidationError) as exc:
            raise RedemptionError(
                "Submission may have succeeded but the response was malformed. Check "
                f"transaction {prepared.preview.transaction_id} before retrying"
            ) from exc
        if transaction_id != prepared.preview.transaction_id:
            raise RedemptionError(
                "Submission returned a different transaction ID. Check both IDs before "
                f"retrying: expected {prepared.preview.transaction_id}, got {transaction_id}"
            )
        return SubmissionResult(transaction_id, estimated_submission_time)


def parse_mainnet_address(value: str, label: str) -> Address:
    normalized = value.strip()
    if not normalized:
        raise InputValidationError(f"{label} is required")
    try:
        address = Address.from_primitive(normalized)
    except (PyCardanoException, TypeError, ValueError) as exc:
        raise InputValidationError(f"{label} is not a valid Cardano address") from exc
    if address.network != Network.MAINNET:
        raise InputValidationError(f"{label} must be a Cardano mainnet address")
    if address.payment_part is None:
        raise InputValidationError(f"{label} must contain a payment credential")
    return address


def parse_thaw_schedule(payload: Mapping[str, Any]) -> ThawSchedule:
    raw_thaws = payload["thaws"]
    if not isinstance(raw_thaws, list):
        raise ApiError("Midnight", 200, "invalid_response", "thaws must be an array")

    thaws = []
    for raw in raw_thaws:
        if not isinstance(raw, Mapping):
            raise ApiError(
                "Midnight", 200, "invalid_response", "thaw entry must be an object"
            )
        try:
            night_subunits = _strict_non_negative_int(raw["amount"], "amount")
            status = str(raw["status"])
            thawing_period_start = str(raw["thawing_period_start"])
            transaction_id_value = raw["transaction_id"]
        except (KeyError, InputValidationError) as exc:
            raise ApiError(
                "Midnight", 200, "invalid_response", "Malformed thaw entry"
            ) from exc
        if status not in PORTAL_THAW_STATUSES:
            raise ApiError(
                "Midnight",
                200,
                "invalid_response",
                f"Unknown thaw status: {status}",
            )
        if transaction_id_value is not None and not isinstance(
            transaction_id_value, str
        ):
            raise ApiError(
                "Midnight",
                200,
                "invalid_response",
                "transaction_id must be a string or null",
            )
        thaws.append(
            Thaw(
                night_subunits=night_subunits,
                status=status,
                thawing_period_start=thawing_period_start,
                transaction_id=transaction_id_value,
            )
        )
    if not thaws:
        raise ApiError("Midnight", 200, "invalid_response", "No thaws returned")
    return ThawSchedule(tuple(thaws))


def _parse_koios_utxo(raw: Any) -> ChainUtxo:
    if not isinstance(raw, Mapping):
        raise ApiError(
            "Koios", 200, "invalid_response", "UTxO entry is not a JSON object"
        )
    try:
        tx_hash = _required_string(raw, "tx_hash")
        tx_index = _required_non_negative_int(raw, "tx_index")
        address_text = _required_string(raw, "address")
        lovelace = _required_non_negative_int(raw, "value")
        is_spent = raw["is_spent"]
        datum_hash = raw["datum_hash"]
        inline_datum = raw["inline_datum"]
        reference_script = raw["reference_script"]
        raw_assets = raw["asset_list"]
    except (KeyError, InputValidationError) as exc:
        raise ApiError(
            "Koios", 200, "invalid_response", "Malformed UTxO entry"
        ) from exc

    try:
        transaction_id = bytes.fromhex(tx_hash)
    except ValueError as exc:
        raise ApiError(
            "Koios", 200, "invalid_response", "UTxO transaction hash is not hex"
        ) from exc
    if len(transaction_id) != 32:
        raise ApiError(
            "Koios", 200, "invalid_response", "UTxO transaction hash must be 32 bytes"
        )
    try:
        parse_mainnet_address(address_text, "Koios UTxO address")
    except InputValidationError as exc:
        raise ApiError(
            "Koios", 200, "invalid_response", "UTxO address is invalid"
        ) from exc
    if not isinstance(is_spent, bool):
        raise ApiError(
            "Koios", 200, "invalid_response", "is_spent must be a boolean"
        )
    if datum_hash is not None and not isinstance(datum_hash, str):
        raise ApiError(
            "Koios", 200, "invalid_response", "datum_hash must be a string or null"
        )
    if inline_datum is not None and not isinstance(inline_datum, Mapping):
        raise ApiError(
            "Koios", 200, "invalid_response", "inline_datum must be an object or null"
        )
    if reference_script is not None and not isinstance(reference_script, Mapping):
        raise ApiError(
            "Koios",
            200,
            "invalid_response",
            "reference_script must be an object or null",
        )
    if not isinstance(raw_assets, list):
        raise ApiError(
            "Koios", 200, "invalid_response", "asset_list must be an array"
        )

    assets = []
    asset_ids: set[tuple[str, str]] = set()
    for raw_asset in raw_assets:
        if not isinstance(raw_asset, Mapping):
            raise ApiError(
                "Koios", 200, "invalid_response", "Asset entry must be an object"
            )
        try:
            policy_id = _required_string(raw_asset, "policy_id")
            asset_name = str(raw_asset["asset_name"])
            quantity = _required_non_negative_int(raw_asset, "quantity")
            bytes.fromhex(policy_id)
            bytes.fromhex(asset_name)
        except (KeyError, InputValidationError, ValueError) as exc:
            raise ApiError(
                "Koios", 200, "invalid_response", "Malformed asset entry"
            ) from exc
        if len(policy_id) != 56:
            raise ApiError(
                "Koios", 200, "invalid_response", "Asset policy ID must be 28 bytes"
            )
        asset_id = (policy_id, asset_name)
        if asset_id in asset_ids:
            raise ApiError(
                "Koios", 200, "invalid_response", "Duplicate asset entry"
            )
        asset_ids.add(asset_id)
        assets.append(NativeAssetAmount(policy_id, asset_name, quantity))

    reference_script_hash = None
    reference_script_type = None
    if reference_script is not None:
        try:
            raw_hash = reference_script["hash"]
            raw_type = reference_script["type"]
        except KeyError as exc:
            raise ApiError(
                "Koios", 200, "invalid_response", "Malformed reference script"
            ) from exc
        if raw_hash is not None and not isinstance(raw_hash, str):
            raise ApiError(
                "Koios",
                200,
                "invalid_response",
                "Reference script hash must be a string or null",
            )
        if raw_type is not None and not isinstance(raw_type, str):
            raise ApiError(
                "Koios",
                200,
                "invalid_response",
                "Reference script type must be a string or null",
            )
        reference_script_hash = raw_hash
        reference_script_type = raw_type

    return ChainUtxo(
        reference=f"{tx_hash}#{tx_index}",
        address=address_text,
        lovelace=lovelace,
        assets=tuple(assets),
        is_spent=is_spent,
        has_datum_hash=datum_hash is not None,
        has_inline_datum=inline_datum is not None,
        has_reference_script=reference_script is not None,
        reference_script_hash=reference_script_hash,
        reference_script_type=reference_script_type,
    )


def build_funding_utxos(
    koios_utxos: Sequence[ChainUtxo],
    derived_addresses: Mapping[str, DerivedAddress],
) -> tuple[FundingUtxo, ...]:
    result = []
    for chain_utxo in koios_utxos:
        derived = derived_addresses.get(chain_utxo.address)
        if derived is None:
            raise TransactionValidationError(
                f"Koios returned an unrequested address: {chain_utxo.address}"
            )
        if chain_utxo.is_spent:
            continue
        if chain_utxo.has_datum_hash:
            continue
        if chain_utxo.has_inline_datum:
            continue
        if chain_utxo.has_reference_script:
            continue
        if chain_utxo.assets:
            continue

        tx_hash, tx_index = chain_utxo.reference.split("#", 1)
        address = parse_mainnet_address(chain_utxo.address, "Koios UTxO address")
        utxo = UTxO(
            TransactionInput(TransactionId(bytes.fromhex(tx_hash)), int(tx_index)),
            TransactionOutput(address, Value(chain_utxo.lovelace)),
        )
        result.append(
            FundingUtxo(
                reference=chain_utxo.reference,
                address=chain_utxo.address,
                derivation_path=derived.derivation_path,
                lovelace=chain_utxo.lovelace,
                cbor=utxo.to_cbor_hex(),
            )
        )
    return tuple(result)


def select_funding_utxos(
    funding_utxos: Sequence[FundingUtxo],
) -> tuple[FundingUtxo, ...]:
    references = [utxo.reference for utxo in funding_utxos]
    if len(set(references)) != len(references):
        raise TransactionValidationError("Funding UTxOs contain duplicate references")

    ordered = sorted(funding_utxos, key=lambda item: (item.lovelace, item.reference))
    best_group: tuple[FundingUtxo, ...] | None = None
    best_key: tuple[int, int, tuple[str, ...]] | None = None

    def consider(group: tuple[FundingUtxo, ...]) -> None:
        nonlocal best_group, best_key
        total_lovelace = sum(utxo.lovelace for utxo in group)
        if total_lovelace < MIN_FUNDING_LOVELACE:
            return
        key = (total_lovelace, len(group), tuple(utxo.reference for utxo in group))
        if best_key is None or key < best_key:
            best_group = group
            best_key = key

    for utxo in ordered:
        consider((utxo,))

    left = 0
    right = len(ordered) - 1
    while left < right:
        pair = (ordered[left], ordered[right])
        if sum(utxo.lovelace for utxo in pair) >= MIN_FUNDING_LOVELACE:
            consider(pair)
            right -= 1
        else:
            left += 1

    for first_index in range(len(ordered) - 2):
        left = first_index + 1
        right = len(ordered) - 1
        while left < right:
            triple = (ordered[first_index], ordered[left], ordered[right])
            if sum(utxo.lovelace for utxo in triple) >= MIN_FUNDING_LOVELACE:
                consider(triple)
                right -= 1
            else:
                left += 1

    if best_group is not None:
        return best_group

    available_lovelace = sum(
        utxo.lovelace
        for utxo in sorted(ordered, key=lambda item: item.lovelace, reverse=True)[
            :MAX_FUNDING_INPUTS
        ]
    )
    available_ada = Decimal(available_lovelace) / 1_000_000
    required_ada = Decimal(MIN_FUNDING_LOVELACE) / 1_000_000
    raise TransactionValidationError(
        "No sufficient pure-ADA UTxOs were found in the scanned addresses: "
        f"{available_ada:f} ADA available, {required_ada:f} ADA required"
    )


def validate_redemption_transaction(
    transaction_cbor: str,
    destination_address: str,
    change_address: str,
    schedule: ThawSchedule,
    selected_utxos: Sequence[FundingUtxo],
    available_signer_key_hashes: AbstractSet[VerificationKeyHash],
    context_utxos: Mapping[str, ChainUtxo],
) -> RedemptionPreview:
    transaction = _decode_transaction(transaction_cbor)
    body = transaction.transaction_body
    _validate_transaction_shape(transaction)
    contract_utxo = _validate_chain_context(
        transaction,
        destination_address,
        schedule,
        selected_utxos,
        context_utxos,
    )
    selected_references = {utxo.reference for utxo in selected_utxos}
    selected_lovelace = sum(utxo.lovelace for utxo in selected_utxos)
    collateral_references, total_collateral = _validate_collateral(
        body,
        selected_utxos,
        change_address,
    )

    if body.required_signers:
        missing_signers = [
            key_hash
            for key_hash in body.required_signers
            if key_hash not in available_signer_key_hashes
        ]
        if missing_signers:
            raise TransactionValidationError(
                f"Required signer is not in the scanned wallet: {missing_signers[0]}"
            )

    output_previews = _validate_redemption_outputs(
        body,
        destination_address,
        change_address,
        schedule,
        selected_utxos,
        contract_utxo,
    )

    return RedemptionPreview(
        destination_address=destination_address,
        change_address=change_address,
        redeemable_night=schedule.redeemable_now,
        fee_ada=Decimal(body.fee) / 1_000_000,
        selected_funding_ada=Decimal(selected_lovelace) / 1_000_000,
        total_collateral_ada=Decimal(total_collateral) / 1_000_000,
        collateral_return_ada=(
            Decimal(selected_lovelace - total_collateral) / 1_000_000
        ),
        selected_inputs=tuple(sorted(selected_references)),
        collateral_inputs=tuple(sorted(collateral_references)),
        outputs=output_previews,
        transaction_id=_exact_transaction_body_hash(transaction_cbor).hex(),
    )


def _validate_transaction_shape(transaction: Transaction) -> None:
    body = transaction.transaction_body
    if transaction.valid is not True:
        raise TransactionValidationError("The backend returned an invalid transaction")
    if transaction.auxiliary_data is not None:
        raise TransactionValidationError("Unexpected auxiliary data in transaction")
    if transaction.transaction_witness_set.vkey_witnesses:
        raise TransactionValidationError(
            "The backend transaction unexpectedly contains payment witnesses"
        )
    if body.fee <= 0 or body.fee > MAX_ALLOWED_FEE_LOVELACE:
        raise TransactionValidationError(
            f"Transaction fee {body.fee} lovelace is outside the allowed range"
        )
    if body.network_id is not None and body.network_id != Network.MAINNET:
        raise TransactionValidationError(
            "Redemption transaction contains a non-mainnet network ID"
        )
    if body.mint:
        raise TransactionValidationError("A redemption transaction must not mint assets")
    if body.certificates:
        raise TransactionValidationError("Unexpected certificates in redemption transaction")
    if body.withdraws:
        raise TransactionValidationError("Unexpected reward withdrawal in transaction")
    if body.voting_procedures:
        raise TransactionValidationError("Unexpected voting procedure in transaction")
    if body.proposal_procedures:
        raise TransactionValidationError("Unexpected governance proposal in transaction")
    if body.update:
        raise TransactionValidationError("Unexpected protocol update in transaction")
    if body.auxiliary_data_hash:
        raise TransactionValidationError("Unexpected metadata hash in transaction")
    if body.current_treasury_value:
        raise TransactionValidationError("Unexpected treasury value in transaction")
    if body.donation:
        raise TransactionValidationError("Unexpected treasury donation in transaction")
    if body.validity_start is None:
        raise TransactionValidationError(
            "Redemption transaction is missing its validity start"
        )
    if body.ttl is not None:
        raise TransactionValidationError(
            "Redemption transaction has an unexpected validity deadline"
        )
    if body.script_data_hash is None:
        raise TransactionValidationError(
            "Redemption transaction is missing its script-data hash"
        )


def _validate_chain_context(
    transaction: Transaction,
    destination_address: str,
    schedule: ThawSchedule,
    selected_utxos: Sequence[FundingUtxo],
    context_utxos: Mapping[str, ChainUtxo],
) -> ChainUtxo:
    contract_reference, script_reference = _redemption_context_references(
        transaction, selected_utxos
    )
    expected_context_references = {contract_reference, script_reference}
    if set(context_utxos) != expected_context_references:
        raise TransactionValidationError(
            "The chain context does not exactly match the transaction references"
        )

    contract_utxo = context_utxos[contract_reference]
    reference_utxo = context_utxos[script_reference]
    destination = parse_mainnet_address(destination_address, "Destination address")
    contract_address = parse_mainnet_address(
        contract_utxo.address, "Redemption contract address"
    )
    if contract_utxo.is_spent:
        raise TransactionValidationError(
            "The redemption contract input was already spent; prepare again"
        )
    if contract_address.payment_part != REDEMPTION_SCRIPT_HASH:
        raise TransactionValidationError(
            "The contract input does not use the official redemption script hash"
        )
    if contract_address.staking_part != destination.staking_part:
        raise TransactionValidationError(
            "The redemption contract stake credential does not match the destination"
        )
    if not contract_utxo.has_inline_datum or contract_utxo.has_reference_script:
        raise TransactionValidationError(
            "The redemption contract input has an unexpected datum or script shape"
        )
    _require_exact_chain_night(
        contract_utxo,
        schedule.total_left_subunits,
        "redemption contract input",
    )

    if reference_utxo.is_spent:
        raise TransactionValidationError(
            "The redemption reference-script input is already spent"
        )
    if (
        reference_utxo.assets
        or reference_utxo.has_datum_hash
        or reference_utxo.has_inline_datum
    ):
        raise TransactionValidationError(
            "The redemption reference input has unexpected assets or datum"
        )
    if (
        not reference_utxo.has_reference_script
        or reference_utxo.reference_script_hash != REDEMPTION_SCRIPT_HASH.payload.hex()
        or reference_utxo.reference_script_type != "plutusV3"
    ):
        raise TransactionValidationError(
            "The reference input does not contain the official Plutus V3 redemption script"
        )
    return contract_utxo


def _validate_collateral(
    body: TransactionBody,
    selected_utxos: Sequence[FundingUtxo],
    change_address: str,
) -> tuple[set[str], int]:
    selected_references = {utxo.reference for utxo in selected_utxos}
    collateral_references = {
        _input_reference(item) for item in (body.collateral or [])
    }
    if collateral_references != selected_references:
        raise TransactionValidationError(
            "Collateral inputs do not exactly match the selected funding inputs"
        )
    total_collateral = body.total_collateral
    if (
        total_collateral is None
        or total_collateral <= 0
        or total_collateral > MAX_ALLOWED_FEE_LOVELACE
    ):
        raise TransactionValidationError(
            "Total collateral is missing or outside the 5 ADA safety limit"
        )
    selected_lovelace = sum(utxo.lovelace for utxo in selected_utxos)
    if total_collateral > selected_lovelace:
        raise TransactionValidationError(
            "Total collateral exceeds the selected pure-ADA inputs"
        )
    expected_collateral_return = selected_lovelace - total_collateral
    collateral_return = body.collateral_return
    if expected_collateral_return > 0:
        if collateral_return is None:
            raise TransactionValidationError(
                "Collateral return is missing from the transaction"
            )
        if (
            str(collateral_return.address) != change_address
            or collateral_return.amount.coin != expected_collateral_return
            or collateral_return.amount.multi_asset
            or collateral_return.datum is not None
            or collateral_return.datum_hash is not None
            or collateral_return.script is not None
        ):
            raise TransactionValidationError(
                "Collateral return does not return the exact ADA balance to change"
            )
    elif collateral_return is not None:
        raise TransactionValidationError("Unexpected collateral return in transaction")
    return collateral_references, total_collateral


def _validate_redemption_outputs(
    body: TransactionBody,
    destination_address: str,
    change_address: str,
    schedule: ThawSchedule,
    selected_utxos: Sequence[FundingUtxo],
    contract_utxo: ChainUtxo,
) -> tuple[TransactionOutputPreview, ...]:
    expected_night = schedule.expected_night_subunits
    expected_continuation_night = schedule.continuation_night_subunits
    destination_outputs: list[TransactionOutput] = []
    change_outputs: list[TransactionOutput] = []
    continuation_outputs: list[TransactionOutput] = []
    output_previews = []
    for output in body.outputs:
        output_address = str(output.address)
        night_subunits = _night_quantity(output.amount.multi_asset)
        has_datum = output.datum is not None or output.datum_hash is not None
        if output_address == destination_address and night_subunits == expected_night:
            destination_outputs.append(output)
        elif output_address == change_address and not output.amount.multi_asset:
            change_outputs.append(output)
        else:
            continuation_outputs.append(output)
        output_previews.append(
            TransactionOutputPreview(
                address=output_address,
                lovelace=output.amount.coin,
                night_subunits=night_subunits,
                has_datum=has_datum,
            )
        )

    if len(destination_outputs) != 1:
        raise TransactionValidationError(
            "Transaction must contain exactly one destination output with the scheduled NIGHT amount"
        )
    destination_output = destination_outputs[0]
    _require_exact_output_night(destination_output, expected_night, "destination")
    if (
        destination_output.amount.coin <= 0
        or destination_output.datum is not None
        or destination_output.datum_hash is not None
        or destination_output.script is not None
    ):
        raise TransactionValidationError(
            "Destination output has an unexpected ADA, datum, or script shape"
        )

    if len(change_outputs) != 1:
        raise TransactionValidationError(
            "Transaction must contain exactly one pure-ADA change output"
        )
    change_output = change_outputs[0]
    if (
        change_output.amount.coin <= 0
        or change_output.datum is not None
        or change_output.datum_hash is not None
        or change_output.script is not None
    ):
        raise TransactionValidationError(
            "Change output has an unexpected ADA, datum, or script shape"
        )

    expected_continuation_count = 1 if expected_continuation_night > 0 else 0
    if len(continuation_outputs) != expected_continuation_count:
        unexpected = [str(output.address) for output in continuation_outputs]
        raise TransactionValidationError(
            "Unexpected continuation/output addresses in transaction: "
            f"{unexpected}"
        )
    if continuation_outputs:
        continuation_output = continuation_outputs[0]
        if str(continuation_output.address) != contract_utxo.address:
            raise TransactionValidationError(
                "Continuation output does not return to the redemption contract"
            )
        _require_exact_output_night(
            continuation_output,
            expected_continuation_night,
            "continuation",
        )
        if (
            continuation_output.amount.coin != contract_utxo.lovelace
            or continuation_output.datum is None
            or continuation_output.datum_hash is not None
            or continuation_output.script is not None
        ):
            raise TransactionValidationError(
                "Continuation output does not preserve contract ADA and inline datum"
            )

    selected_lovelace = sum(utxo.lovelace for utxo in selected_utxos)
    total_input_lovelace = selected_lovelace + contract_utxo.lovelace
    total_output_lovelace = sum(output.amount.coin for output in body.outputs)
    if total_input_lovelace != total_output_lovelace + body.fee:
        raise TransactionValidationError(
            "ADA balance across funding, contract, outputs, and fee is inconsistent"
        )

    return tuple(output_previews)


def _redemption_context_references(
    transaction: Transaction,
    selected_utxos: Sequence[FundingUtxo],
) -> tuple[str, str]:
    selected_references = {utxo.reference for utxo in selected_utxos}
    if len(selected_references) != len(selected_utxos):
        raise TransactionValidationError("Selected funding inputs contain duplicates")
    body_references = {
        _input_reference(transaction_input)
        for transaction_input in transaction.transaction_body.inputs
    }
    missing_funding = selected_references - body_references
    if missing_funding:
        raise TransactionValidationError(
            "Built transaction does not consume selected funding inputs: "
            f"{sorted(missing_funding)}"
        )
    contract_references = body_references - selected_references
    if len(contract_references) != 1 or len(body_references) != len(selected_references) + 1:
        raise TransactionValidationError(
            "Redemption must contain exactly one contract input plus the selected funding inputs"
        )
    reference_inputs = transaction.transaction_body.reference_inputs or []
    if len(reference_inputs) != 1:
        raise TransactionValidationError(
            "Redemption must contain exactly one reference-script input"
        )
    return next(iter(contract_references)), _input_reference(reference_inputs[0])


def _require_exact_chain_night(
    utxo: ChainUtxo, expected_subunits: int, label: str
) -> None:
    expected_asset = NativeAssetAmount(
        NIGHT_POLICY_ID.payload.hex(),
        NIGHT_ASSET_NAME.payload.hex(),
        expected_subunits,
    )
    if utxo.assets != (expected_asset,):
        raise TransactionValidationError(
            f"The {label} does not contain exactly {expected_subunits} NIGHT subunits"
        )


def _require_exact_output_night(
    output: TransactionOutput, expected_subunits: int, label: str
) -> None:
    expected_assets = {
        (NIGHT_POLICY_ID.payload, NIGHT_ASSET_NAME.payload): expected_subunits
    }
    actual_assets = {
        (policy_id.payload, asset_name.payload): int(quantity)
        for policy_id, policy_assets in output.amount.multi_asset.items()
        for asset_name, quantity in policy_assets.items()
    }
    if actual_assets != expected_assets:
        raise TransactionValidationError(
            f"The {label} output does not contain exactly {expected_subunits} NIGHT subunits"
        )


def _night_quantity(multi_asset: MultiAsset) -> int:
    policy_assets = multi_asset.get(NIGHT_POLICY_ID)
    if policy_assets is None:
        return 0
    if NIGHT_ASSET_NAME not in policy_assets:
        return 0
    return int(policy_assets[NIGHT_ASSET_NAME])


def _decode_transaction(transaction_cbor: str) -> Transaction:
    if not isinstance(transaction_cbor, str) or not transaction_cbor:
        raise TransactionValidationError("The backend returned no transaction CBOR")
    try:
        transaction = Transaction.from_cbor(transaction_cbor)
    except (PyCardanoException, TypeError, ValueError) as exc:
        raise TransactionValidationError(
            "The backend returned malformed transaction CBOR"
        ) from exc
    if not isinstance(transaction, Transaction):
        raise TransactionValidationError("Decoded CBOR is not a Cardano transaction")
    return transaction


def _exact_transaction_body_hash(transaction_cbor: str) -> bytes:
    """Hash the original transaction-body bytes without reserializing them."""
    try:
        raw_transaction = bytes.fromhex(transaction_cbor)
        offset = 0
        major_type, argument, offset = _read_cbor_head(raw_transaction, offset)
        while major_type == 6:
            major_type, argument, offset = _read_cbor_head(raw_transaction, offset)
        if major_type != 4 or argument != 4:
            raise ValueError("Cardano transaction is not a four-item CBOR array")

        body_stream = BytesIO(raw_transaction[offset:])
        cbor2.CBORDecoder(body_stream).decode()
        body_end = offset + body_stream.tell()
    except (cbor2.CBORDecodeError, IndexError, TypeError, ValueError) as exc:
        raise TransactionValidationError(
            "Could not isolate the original Cardano transaction body"
        ) from exc
    if body_end <= offset:
        raise TransactionValidationError("Cardano transaction body is empty")
    return hashlib.blake2b(
        raw_transaction[offset:body_end],
        digest_size=32,
    ).digest()


def _read_cbor_head(data: bytes, offset: int) -> tuple[int, int, int]:
    if offset >= len(data):
        raise ValueError("Unexpected end of CBOR")
    initial_byte = data[offset]
    major_type = initial_byte >> 5
    additional_info = initial_byte & 0x1F
    offset += 1
    if additional_info < 24:
        return major_type, additional_info, offset
    byte_lengths = {24: 1, 25: 2, 26: 4, 27: 8}
    if additional_info not in byte_lengths:
        raise ValueError("Indefinite or reserved CBOR head is not supported")
    byte_length = byte_lengths[additional_info]
    end = offset + byte_length
    if end > len(data):
        raise ValueError("Truncated CBOR head")
    argument = int.from_bytes(data[offset:end], "big")
    return major_type, argument, end


def _input_reference(transaction_input: TransactionInput) -> str:
    return f"{transaction_input.transaction_id}#{transaction_input.index}"


def _decode_json_response(response: requests.Response, service: str) -> Any:
    if not response.text:
        if 200 <= response.status_code < 300:
            raise ApiError(
                service,
                response.status_code,
                "invalid_response",
                "Successful response had an empty body",
            )
        return {"type": "empty_response", "message": "Empty response body"}
    try:
        return json.loads(response.text, parse_float=Decimal)
    except json.JSONDecodeError as exc:
        raise ApiError(
            service,
            response.status_code,
            "invalid_response",
            "Response was not valid JSON",
            response.text[:300],
        ) from exc


def _api_error_from_payload(
    service: str, status_code: int, payload: Any
) -> ApiError:
    if isinstance(payload, Mapping):
        error_type = str(payload["type"]) if "type" in payload else "request_failed"
        if "message" in payload:
            message = str(payload["message"])
        elif "error" in payload:
            message = str(payload["error"])
        else:
            message = "Request failed"
        info = str(payload["info"]) if "info" in payload else None
        return ApiError(service, status_code, error_type, message, info)
    return ApiError(
        service,
        status_code,
        "request_failed",
        f"Unexpected error payload: {payload!r}",
    )


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value:
        raise InputValidationError(f"{key} must be a non-empty string")
    return value


def _required_non_negative_int(payload: Mapping[str, Any], key: str) -> int:
    return _strict_non_negative_int(payload[key], key)


def _strict_non_negative_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise InputValidationError(f"{label} must be an integer")
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise InputValidationError(f"{label} must be an integer") from exc
    if not decimal_value.is_finite() or decimal_value != decimal_value.to_integral_value():
        raise InputValidationError(f"{label} must be an integer")
    if decimal_value < 0:
        raise InputValidationError(f"{label} cannot be negative")
    return int(decimal_value)


def _chunks(values: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Redeem thawed NIGHT using a connected Trezor"
    )
    parser.add_argument(
        "--account",
        type=int,
        default=0,
        help="CIP-1852 account index (Trezor Suite Account #1 is index 0)",
    )
    parser.add_argument(
        "--scan-limit",
        type=int,
        default=DEFAULT_SCAN_LIMIT,
        help=f"external and internal addresses to scan (1-{MAX_SCAN_LIMIT})",
    )
    parser.add_argument(
        "--derivation",
        choices=sorted(SUPPORTED_DERIVATION_TYPES),
        default="icarus",
        help=(
            "icarus for current Trezor accounts; icarus_trezor for the historic "
            "24-word Trezor Cardano derivation"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_argument_parser().parse_args(argv)
    print("Midnight NIGHT Redemption - Cardano")
    print("Seed and private keys stay on the Trezor.")
    print("If enabled, enter the passphrase only on the Trezor display.")
    destination_address = input("Destination address (addr1...): ").strip()

    workflow = RedemptionWorkflow()
    try:
        prepared = workflow.prepare(
            destination_address=destination_address,
            account_index=args.account,
            scan_limit=args.scan_limit,
            derivation_type=args.derivation,
        )
        print()
        print(prepared.preview.to_text())
        print()
        confirmation = input(
            "Type REDEEM to sign and submit this exact transaction: "
        ).strip()
        if confirmation != "REDEEM":
            print("Cancelled; nothing was signed or submitted.")
            return 2

        result = workflow.submit(prepared)
        print(f"Submitted successfully. Transaction ID: {result.transaction_id}")
        print(
            "Estimated submission time: "
            f"{result.estimated_submission_time} seconds"
        )
        return 0
    except (KeyError, RedemptionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(
            f"UNEXPECTED ERROR: {type(exc).__name__} (details suppressed)",
            file=sys.stderr,
        )
        traceback.print_tb(exc.__traceback__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
