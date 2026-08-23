"""Trezor-backed Cardano address derivation and transaction witnesses.

The seed and private keys never enter this process.  If passphrase protection is
enabled, the passphrase is accepted only on-device. Public addresses are read
from the device, and the already-validated transaction body is streamed back to
the Trezor for physical approval and signing.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

import cbor2
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from pycardano import (
    Address,
    Network,
    PaymentVerificationKey,
    PyCardanoException,
    Transaction,
    TransactionInput,
    TransactionOutput,
    TransactionWitnessSet,
    VerificationKeyHash,
    VerificationKeyWitness,
)
from trezorlib import cardano as trezor_cardano
from trezorlib import exceptions as trezor_exceptions
from trezorlib import messages as trezor_messages
from trezorlib import tools as trezor_tools
from trezorlib.client import PassphraseSetting, get_default_client


APP_NAME = "MidnightClaimer"
MAINNET_PROTOCOL_MAGIC = trezor_cardano.PROTOCOL_MAGICS["mainnet"]
MAINNET_NETWORK_ID = trezor_cardano.NETWORK_IDS["mainnet"]
TAG_CBOR_SET = 258


class TrezorHardwareError(RuntimeError):
    """A safe, actionable Trezor connection or signing failure."""


@dataclass(frozen=True)
class TrezorPublicAddress:
    address: str
    derivation_path: str


@dataclass(frozen=True)
class TrezorWalletSnapshot:
    addresses: tuple[TrezorPublicAddress, ...]
    verified_destination: TrezorPublicAddress
    label: str
    model: str
    firmware: str

    @property
    def description(self) -> str:
        label = self.label.strip()
        if not label:
            label = "Trezor"
        return f"{label} ({self.model}, Firmware {self.firmware})"


@dataclass(frozen=True)
class TrezorSigningRequest:
    signing_mode: trezor_messages.CardanoTxSigningMode
    inputs: list[trezor_cardano.InputWithPath]
    outputs: list[trezor_cardano.OutputWithData]
    fee: int
    ttl: int | None
    validity_interval_start: int | None
    script_data_hash: bytes
    collateral_inputs: list[trezor_cardano.CollateralInputWithPath]
    required_signers: list[trezor_messages.CardanoTxRequiredSigner]
    collateral_return: trezor_cardano.OutputWithData | None
    total_collateral: int | None
    reference_inputs: list[trezor_messages.CardanoTxReferenceInput]
    derivation_type: trezor_messages.CardanoDerivationType
    include_network_id: bool
    tag_cbor_sets: bool
    expected_key_hash_by_path: Mapping[tuple[int, ...], VerificationKeyHash]


def derive_base_addresses(
    account_index: int,
    scan_limit: int,
    derivation_type: str,
    *,
    verification_address: str,
) -> TrezorWalletSnapshot:
    """Read addresses and prove that the device wallet owns the destination."""
    if account_index < 0 or account_index > 100:
        raise TrezorHardwareError("Account index must be between 0 and 100")
    if scan_limit < 1 or scan_limit > 100:
        raise TrezorHardwareError("Address scan limit must be between 1 and 100")

    try:
        expected_destination = Address.from_primitive(verification_address)
    except (PyCardanoException, TypeError, ValueError) as exc:
        raise TrezorHardwareError(
            "Midnight destination address is malformed"
        ) from exc
    if expected_destination.network != Network.MAINNET:
        raise TrezorHardwareError(
            "Midnight destination address is not a Cardano mainnet address"
        )
    expected_destination_text = str(expected_destination)

    trezor_derivation = _derivation_type(derivation_type)
    stake_path = f"m/1852'/1815'/{account_index}'/2/0"
    addresses: list[TrezorPublicAddress] = []
    verified_destination: TrezorPublicAddress | None = None

    with _open_cardano_session() as (client, session):
        for role in (0, 1):
            for address_index in range(scan_limit):
                payment_path = (
                    f"m/1852'/1815'/{account_index}'/{role}/{address_index}"
                )
                parameters = trezor_cardano.create_address_parameters(
                    trezor_messages.CardanoAddressType.BASE,
                    trezor_tools.parse_path(payment_path),
                    trezor_tools.parse_path(stake_path),
                )
                address = trezor_cardano.get_address(
                    session,
                    parameters,
                    protocol_magic=MAINNET_PROTOCOL_MAGIC,
                    network_id=MAINNET_NETWORK_ID,
                    show_display=False,
                    derivation_type=trezor_derivation,
                )
                # Refuse non-mainnet or malformed device output before it reaches
                # Koios or Midnight.
                try:
                    parsed = Address.from_primitive(address)
                except (PyCardanoException, TypeError, ValueError) as exc:
                    raise TrezorHardwareError(
                        "Trezor returned a malformed Cardano address"
                    ) from exc
                if parsed.network != Network.MAINNET:
                    raise TrezorHardwareError(
                        "Trezor returned a non-mainnet Cardano address"
                    )
                public_address = TrezorPublicAddress(str(parsed), payment_path)
                addresses.append(public_address)

                if public_address.address == expected_destination_text:
                    if verified_destination is not None:
                        raise TrezorHardwareError(
                            "Trezor derived the Midnight destination at multiple paths"
                        )
                    displayed_address = trezor_cardano.get_address(
                        session,
                        parameters,
                        protocol_magic=MAINNET_PROTOCOL_MAGIC,
                        network_id=MAINNET_NETWORK_ID,
                        show_display=True,
                        derivation_type=trezor_derivation,
                    )
                    try:
                        displayed_destination = Address.from_primitive(
                            displayed_address
                        )
                    except (PyCardanoException, TypeError, ValueError) as exc:
                        raise TrezorHardwareError(
                            "Trezor displayed a malformed Cardano address"
                        ) from exc
                    if str(displayed_destination) != expected_destination_text:
                        raise TrezorHardwareError(
                            "Trezor displayed a different address than the verified "
                            "Midnight destination"
                        )
                    verified_destination = public_address

        if verified_destination is None:
            raise TrezorHardwareError(
                "Die Passphrase-Wallet passt nicht zur Midnight-Zieladresse im "
                "gescannten Bereich. Passphrase, Ableitung, Account Index und "
                "Scan-Limit pruefen; nichts wurde signiert oder gesendet."
            )

        features = client.features
        label = features.label if isinstance(features.label, str) else ""
        model = (
            features.internal_model
            if isinstance(features.internal_model, str)
            else ""
        )
        if not model and isinstance(features.model, str):
            model = features.model
        if not model:
            model = "unknown model"
        return TrezorWalletSnapshot(
            addresses=tuple(addresses),
            verified_destination=verified_destination,
            label=label,
            model=model,
            firmware=(
                f"{features.major_version}.{features.minor_version}."
                f"{features.patch_version}"
            ),
        )


def build_signing_request(
    transaction_cbor: str,
    reference_paths: Mapping[str, str],
    key_hash_by_path: Mapping[str, VerificationKeyHash],
    change_address: str,
    account_index: int,
    derivation_type: str,
) -> TrezorSigningRequest:
    """Convert an exact Cardano body into the official trezorlib model."""
    try:
        transaction = Transaction.from_cbor(transaction_cbor)
    except (PyCardanoException, TypeError, ValueError) as exc:
        raise TrezorHardwareError(
            "The prepared Cardano transaction is invalid"
        ) from exc

    body = transaction.transaction_body
    raw_body = _decode_raw_transaction_body(transaction_cbor)
    try:
        raw_outputs = raw_body[1]
    except KeyError as exc:
        raise TrezorHardwareError("Transaction body is missing its outputs") from exc
    if not isinstance(raw_outputs, list) or len(raw_outputs) != len(body.outputs):
        raise TrezorHardwareError("Transaction output encoding is inconsistent")

    change_path = _path_for_address(change_address, key_hash_by_path)
    stake_path = f"m/1852'/1815'/{account_index}'/2/0"
    trezor_derivation = _derivation_type(derivation_type)

    inputs = []
    expected_by_parsed_path: dict[tuple[int, ...], VerificationKeyHash] = {}
    for transaction_input in body.inputs:
        reference = _input_reference(transaction_input)
        if reference in reference_paths:
            path = reference_paths[reference]
            if path not in key_hash_by_path:
                raise TrezorHardwareError(
                    f"No Trezor public key matches funding input {reference}"
                )
        else:
            path = ""
        inputs.append(
            trezor_cardano.parse_input(
                {
                    "prev_hash": transaction_input.transaction_id.payload.hex(),
                    "prev_index": transaction_input.index,
                    "path": path,
                }
            )
        )
        if path:
            expected_by_parsed_path[tuple(trezor_tools.parse_path(path))] = (
                key_hash_by_path[path]
            )

    outputs = [
        _parse_output(output, raw_output, change_address, change_path, stake_path)
        for output, raw_output in zip(body.outputs, raw_outputs, strict=True)
    ]

    collateral_inputs = []
    collateral_source = () if body.collateral is None else body.collateral
    for transaction_input in collateral_source:
        reference = _input_reference(transaction_input)
        if reference not in reference_paths:
            raise TrezorHardwareError(
                f"No Trezor path matches collateral input {reference}"
            )
        path = reference_paths[reference]
        if path not in key_hash_by_path:
            raise TrezorHardwareError(
                f"No Trezor public key matches collateral input {reference}"
            )
        collateral_inputs.append(
            trezor_cardano.parse_collateral_input(
                {
                    "prev_hash": transaction_input.transaction_id.payload.hex(),
                    "prev_index": transaction_input.index,
                    "path": path,
                }
            )
        )
        expected_by_parsed_path[tuple(trezor_tools.parse_path(path))] = (
            key_hash_by_path[path]
        )

    required_signers = []
    path_by_key_hash = {value: path for path, value in key_hash_by_path.items()}
    required_signer_source = (
        () if body.required_signers is None else body.required_signers
    )
    for key_hash in required_signer_source:
        if key_hash not in path_by_key_hash:
            raise TrezorHardwareError(
                f"No Trezor path matches required signer {key_hash}"
            )
        path = path_by_key_hash[key_hash]
        required_signers.append(
            trezor_cardano.parse_required_signer({"key_path": path})
        )
        expected_by_parsed_path[tuple(trezor_tools.parse_path(path))] = key_hash

    if body.collateral_return is None:
        collateral_return = None
    else:
        if 16 not in raw_body:
            raise TrezorHardwareError(
                "Transaction collateral-return encoding is inconsistent"
            )
        collateral_return = _parse_output(
            body.collateral_return,
            raw_body[16],
            change_address,
            change_path,
            stake_path,
        )
    reference_input_source = (
        () if body.reference_inputs is None else body.reference_inputs
    )
    reference_inputs = [
        trezor_cardano.parse_reference_input(
            {
                "prev_hash": item.transaction_id.payload.hex(),
                "prev_index": item.index,
            }
        )
        for item in reference_input_source
    ]

    if body.script_data_hash is None:
        raise TrezorHardwareError("Transaction is missing its script-data hash")
    if not expected_by_parsed_path:
        raise TrezorHardwareError("Transaction contains no Trezor-owned signer")

    return TrezorSigningRequest(
        signing_mode=trezor_messages.CardanoTxSigningMode.PLUTUS_TRANSACTION,
        inputs=inputs,
        outputs=outputs,
        fee=body.fee,
        ttl=body.ttl,
        validity_interval_start=body.validity_start,
        script_data_hash=body.script_data_hash.payload,
        collateral_inputs=collateral_inputs,
        required_signers=required_signers,
        collateral_return=collateral_return,
        total_collateral=body.total_collateral,
        reference_inputs=reference_inputs,
        derivation_type=trezor_derivation,
        include_network_id=body.network_id is not None,
        tag_cbor_sets=_uses_tagged_cbor_sets(raw_body),
        expected_key_hash_by_path=expected_by_parsed_path,
    )


def create_witness_set(
    transaction_cbor: str,
    expected_transaction_id: str,
    reference_paths: Mapping[str, str],
    key_hash_by_path: Mapping[str, VerificationKeyHash],
    change_address: str,
    account_index: int,
    derivation_type: str,
) -> str:
    """Ask Trezor to sign and verify every returned witness before submit."""
    request = build_signing_request(
        transaction_cbor,
        reference_paths,
        key_hash_by_path,
        change_address,
        account_index,
        derivation_type,
    )
    try:
        expected_hash = bytes.fromhex(expected_transaction_id)
    except ValueError as exc:
        raise TrezorHardwareError("Expected transaction ID is not valid hex") from exc
    if len(expected_hash) != 32:
        raise TrezorHardwareError("Expected transaction ID must be 32 bytes")

    response = _sign_on_device(request)
    try:
        device_hash = response["tx_hash"]
        witnesses = response["witnesses"]
    except (KeyError, TypeError) as exc:
        raise TrezorHardwareError(
            "Trezor returned an incomplete Cardano signing response"
        ) from exc
    if device_hash != expected_hash:
        raise TrezorHardwareError(
            "Trezor signed a different transaction body hash; nothing was submitted"
        )

    expected_key_hashes = frozenset(request.expected_key_hash_by_path.values())
    if not isinstance(witnesses, list) or len(witnesses) != len(expected_key_hashes):
        raise TrezorHardwareError(
            "Trezor returned an unexpected number of Cardano witnesses"
        )

    verified_witnesses = []
    verified_key_hashes: set[VerificationKeyHash] = set()
    for witness in witnesses:
        if not isinstance(witness, Mapping):
            raise TrezorHardwareError("Trezor returned a malformed Cardano witness")
        try:
            witness_type = witness["type"]
            public_key = witness["pub_key"]
            signature = witness["signature"]
        except KeyError as exc:
            raise TrezorHardwareError(
                "Trezor returned an incomplete Cardano witness"
            ) from exc
        if witness_type != trezor_messages.CardanoTxWitnessType.SHELLEY_WITNESS:
            raise TrezorHardwareError("Trezor returned a non-Shelley witness")
        if not isinstance(public_key, bytes) or len(public_key) != 32:
            raise TrezorHardwareError("Trezor returned an invalid public key")
        if not isinstance(signature, bytes) or len(signature) != 64:
            raise TrezorHardwareError("Trezor returned an invalid signature")

        try:
            verification_key = PaymentVerificationKey.from_primitive(public_key)
        except (PyCardanoException, TypeError, ValueError) as exc:
            raise TrezorHardwareError(
                "Trezor returned an invalid payment verification key"
            ) from exc
        key_hash = verification_key.hash()
        if key_hash not in expected_key_hashes:
            raise TrezorHardwareError(
                "The passphrase wallet used for signing does not match the prepared wallet"
            )
        if key_hash in verified_key_hashes:
            raise TrezorHardwareError("Trezor returned a duplicate Cardano witness")
        try:
            VerifyKey(public_key).verify(expected_hash, signature)
        except BadSignatureError as exc:
            raise TrezorHardwareError(
                "A Trezor signature failed local verification"
            ) from exc
        verified_witnesses.append(
            VerificationKeyWitness(verification_key, signature)
        )
        verified_key_hashes.add(key_hash)

    if verified_key_hashes != expected_key_hashes:
        raise TrezorHardwareError("Trezor did not sign with every expected payment key")

    return TransactionWitnessSet(vkey_witnesses=verified_witnesses).to_cbor_hex()


def _sign_on_device(request: TrezorSigningRequest) -> Mapping[str, Any]:
    with _open_cardano_session() as (_, session):
        return trezor_cardano.sign_tx(
            session,
            request.signing_mode,
            request.inputs,
            request.outputs,
            request.fee,
            request.ttl,
            request.validity_interval_start,
            script_data_hash=request.script_data_hash,
            collateral_inputs=request.collateral_inputs,
            required_signers=request.required_signers,
            collateral_return=request.collateral_return,
            total_collateral=request.total_collateral,
            reference_inputs=request.reference_inputs,
            derivation_type=request.derivation_type,
            include_network_id=request.include_network_id,
            tag_cbor_sets=request.tag_cbor_sets,
        )


@contextmanager
def _open_cardano_session() -> Iterator[tuple[Any, Any]]:
    """Open a Cardano session without accepting wallet secrets on the host."""
    session = None
    try:
        client = get_default_client(
            APP_NAME,
            button_callback=lambda _message: None,
            pin_callback=_reject_host_pin,
        )
        client.ensure_unlocked()
        features = client.features
        if features.passphrase_protection is True:
            capabilities = features.capabilities
            if (
                capabilities is None
                or trezor_messages.Capability.PassphraseEntry not in capabilities
            ):
                raise TrezorHardwareError(
                    "This Trezor cannot accept the passphrase on-device. "
                    "For safety, MidnightClaimer refuses host-side passphrase entry."
                )
            passphrase_setting = PassphraseSetting.ON_DEVICE
        elif features.passphrase_protection is False:
            passphrase_setting = PassphraseSetting.STANDARD_WALLET
        else:
            raise TrezorHardwareError(
                "Trezor did not report whether passphrase protection is enabled"
            )
        session = client.get_session(
            passphrase=passphrase_setting,
            derive_cardano=True,
        )
        yield client, session
    except TrezorHardwareError:
        raise
    except trezor_exceptions.Cancelled as exc:
        raise TrezorHardwareError(
            "Trezor operation was cancelled; nothing was submitted"
        ) from exc
    except (trezor_exceptions.TrezorException, OSError, RuntimeError, ValueError) as exc:
        name = type(exc).__name__
        raise TrezorHardwareError(
            f"Trezor connection/signing failed ({name}). Close Trezor Suite and "
            "browser wallets, reconnect and unlock the device."
        ) from exc
    finally:
        if session is not None and not session.is_invalid:
            session.close()


def _reject_host_pin(_request: Any) -> str:
    raise TrezorHardwareError(
        "Trezor requested PIN entry on the computer. Unlock the device on its "
        "screen; MidnightClaimer refuses host-side PIN entry."
    )


def _derivation_type(value: str) -> trezor_messages.CardanoDerivationType:
    if value == "icarus":
        return trezor_messages.CardanoDerivationType.ICARUS
    if value == "icarus_trezor":
        return trezor_messages.CardanoDerivationType.ICARUS_TREZOR
    raise TrezorHardwareError(f"Unsupported Trezor derivation type: {value}")


def _input_reference(transaction_input: TransactionInput) -> str:
    return (
        f"{transaction_input.transaction_id.payload.hex()}"
        f"#{transaction_input.index}"
    )


def _path_for_address(
    address: str,
    key_hash_by_path: Mapping[str, VerificationKeyHash],
) -> str:
    try:
        parsed = Address.from_primitive(address)
    except (PyCardanoException, TypeError, ValueError) as exc:
        raise TrezorHardwareError("Change address is malformed") from exc
    payment_part = parsed.payment_part
    if not isinstance(payment_part, VerificationKeyHash):
        raise TrezorHardwareError("Change address is not controlled by a payment key")
    for path, key_hash in key_hash_by_path.items():
        if key_hash == payment_part:
            return path
    raise TrezorHardwareError("No Trezor derivation path matches the change address")


def _parse_output(
    output: TransactionOutput,
    raw_output: Any,
    change_address: str,
    change_path: str,
    stake_path: str,
) -> trezor_cardano.OutputWithData:
    output_data: dict[str, Any] = {"amount": output.amount.coin}
    raw_datum_kind: str | None = None

    if isinstance(raw_output, Mapping):
        output_data["format"] = (
            trezor_messages.CardanoTxOutputSerializationFormat.MAP_BABBAGE
        )
        if 3 in raw_output or output.script is not None:
            raise TrezorHardwareError(
                "Reference scripts in new outputs are not supported by this signer"
            )
        if 2 in raw_output:
            datum_option = raw_output[2]
            if not isinstance(datum_option, list) or len(datum_option) != 2:
                raise TrezorHardwareError("Transaction contains malformed output datum")
            datum_type, datum_payload = datum_option
            if datum_type == 0:
                if not isinstance(datum_payload, bytes) or len(datum_payload) != 32:
                    raise TrezorHardwareError(
                        "Transaction contains malformed output datum hash"
                    )
                if (
                    output.datum_hash is None
                    or output.datum_hash.payload != datum_payload
                ):
                    raise TrezorHardwareError(
                        "Transaction output datum hash is inconsistent"
                    )
                output_data["datum_hash"] = datum_payload.hex()
                raw_datum_kind = "hash"
            elif datum_type == 1:
                if output.datum is None:
                    raise TrezorHardwareError(
                        "Transaction inline datum is inconsistent"
                    )
                if (
                    not isinstance(datum_payload, cbor2.CBORTag)
                    or datum_payload.tag != 24
                    or not isinstance(datum_payload.value, bytes)
                    or not datum_payload.value
                ):
                    raise TrezorHardwareError(
                        "Transaction inline datum is not embedded CBOR"
                    )
                output_data["inline_datum"] = datum_payload.value.hex()
                raw_datum_kind = "inline"
            else:
                raise TrezorHardwareError(
                    "Transaction contains an unsupported output datum type"
                )
    elif isinstance(raw_output, list):
        output_data["format"] = (
            trezor_messages.CardanoTxOutputSerializationFormat.ARRAY_LEGACY
        )
        if len(raw_output) not in (2, 3):
            raise TrezorHardwareError("Transaction contains malformed legacy output")
        if len(raw_output) == 3:
            datum_hash = raw_output[2]
            if not isinstance(datum_hash, bytes) or len(datum_hash) != 32:
                raise TrezorHardwareError(
                    "Transaction contains malformed legacy datum hash"
                )
            if output.datum_hash is None or output.datum_hash.payload != datum_hash:
                raise TrezorHardwareError(
                    "Transaction legacy datum hash is inconsistent"
                )
            output_data["datum_hash"] = datum_hash.hex()
            raw_datum_kind = "hash"
    else:
        raise TrezorHardwareError("Transaction contains an unknown output encoding")

    if output.datum_hash is not None and raw_datum_kind != "hash":
        raise TrezorHardwareError("Transaction output datum hash is inconsistent")
    if output.datum is not None and raw_datum_kind != "inline":
        raise TrezorHardwareError("Transaction inline datum is inconsistent")

    if str(output.address) == change_address:
        output_data.update(
            {
                "addressType": trezor_messages.CardanoAddressType.BASE,
                "path": change_path,
                "stakingPath": stake_path,
            }
        )
    else:
        output_data["address"] = str(output.address)

    if output.amount.multi_asset:
        output_data["token_bundle"] = [
            {
                "policy_id": policy_id.payload.hex(),
                "tokens": [
                    {
                        "asset_name_bytes": asset_name.payload.hex(),
                        "amount": quantity,
                    }
                    for asset_name, quantity in assets.items()
                ],
            }
            for policy_id, assets in output.amount.multi_asset.items()
        ]
    try:
        return trezor_cardano.parse_output(output_data)
    except (KeyError, TypeError, ValueError) as exc:
        raise TrezorHardwareError(
            "Transaction output cannot be represented for Trezor signing"
        ) from exc


def _uses_tagged_cbor_sets(body: Mapping[int, Any]) -> bool:
    tagged_states = []
    for field_number in (0, 13, 14, 18):
        if field_number not in body:
            continue
        value = body[field_number]
        if isinstance(value, (set, frozenset)):
            tagged_states.append(True)
        elif isinstance(value, list):
            tagged_states.append(False)
        elif isinstance(value, cbor2.CBORTag) and value.tag == TAG_CBOR_SET:
            tagged_states.append(True)
        else:
            raise TrezorHardwareError("Transaction has an unknown CBOR set encoding")
    if not tagged_states:
        raise TrezorHardwareError("Transaction body contains no input set")
    if len(set(tagged_states)) != 1:
        raise TrezorHardwareError("Transaction mixes tagged and untagged CBOR sets")
    return tagged_states[0]


def _decode_raw_transaction_body(transaction_cbor: str) -> Mapping[int, Any]:
    try:
        transaction = cbor2.loads(bytes.fromhex(transaction_cbor))
        transaction_value = (
            transaction.value if isinstance(transaction, cbor2.CBORTag) else transaction
        )
        if not isinstance(transaction_value, list) or not transaction_value:
            raise TypeError("Cardano transaction must be a non-empty array")
        body = transaction_value[0]
    except (TypeError, ValueError, IndexError, KeyError) as exc:
        raise TrezorHardwareError("Could not inspect Cardano transaction CBOR") from exc
    if not isinstance(body, Mapping):
        raise TrezorHardwareError("Cardano transaction body is not a CBOR map")
    if not all(isinstance(key, int) for key in body):
        raise TrezorHardwareError("Cardano transaction body has invalid field keys")
    return body
