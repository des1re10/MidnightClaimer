from __future__ import annotations

import inspect
import sys
from contextlib import contextmanager
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests
from nacl.signing import SigningKey
from pycardano import (
    Address,
    Asset,
    MultiAsset,
    Network,
    PaymentVerificationKey,
    RawPlutusData,
    ScriptDataHash,
    ScriptHash,
    Transaction,
    TransactionBody,
    TransactionId,
    TransactionInput,
    TransactionOutput,
    TransactionWitnessSet,
    Value,
)
from trezorlib import messages as trezor_messages
from trezorlib.client import PassphraseSetting


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CARDANO_CLAIM_DIR = REPOSITORY_ROOT / "cardano-claim"
sys.path.insert(0, str(CARDANO_CLAIM_DIR))

import midnight_redeem_cardano as redemption  # noqa: E402
import trezor_cardano_signer as trezor_signer  # noqa: E402


DESTINATION = (
    "addr1q9xvgr4ehvu5k5tmaly7ugpnvekpqvnxj8xy50pa7kyetlnhel389pa4rnq6"
    "fmkzwsaynmw0mnldhlmchn2sfd589fgsz9dd0y"
)
FUNDING_ADDRESS = (
    "addr1q8m50vdutylp8ju3cwudqy2qj5wh5grh469xgnuvj3vq9s5xttc7l65a369"
    "kkq9re6nlxt77kyjs57xy4yw3qlrl3lcqcf6kkq"
)
CHANGE_ADDRESS = (
    "addr1qy62zdagx8fgsfuyn46dqgmt87wlz8msa347mzhmrr984lvxttc7l65a369k"
    "kq9re6nlxt77kyjs57xy4yw3qlrl3lcq57yu3k"
)
FUNDING_PATH = "m/1852'/1815'/0'/0/0"
CHANGE_PATH = "m/1852'/1815'/0'/1/0"


def thaw_schedule() -> redemption.ThawSchedule:
    return redemption.ThawSchedule(
        (
            redemption.Thaw(10_000_000_001, "confirmed", "a", "tx-1"),
            redemption.Thaw(20_000_000_002, "confirmed", "b", "tx-2"),
            redemption.Thaw(30_000_000_003, "redeemable", "c", None),
            redemption.Thaw(40_000_000_004, "upcoming", "d", None),
        )
    )


def funding_fixture() -> redemption.FundingUtxo:
    return redemption.FundingUtxo(
        reference=f"{'11' * 32}#0",
        address=FUNDING_ADDRESS,
        derivation_path=FUNDING_PATH,
        lovelace=10_000_000,
        cbor="00",
    )


def chain_context() -> dict[str, redemption.ChainUtxo]:
    destination = Address.from_primitive(DESTINATION)
    contract_address = Address(
        redemption.REDEMPTION_SCRIPT_HASH,
        destination.staking_part,
        Network.MAINNET,
    )
    reference_address = Address(
        ScriptHash(bytes.fromhex("55" * 28)),
        None,
        Network.MAINNET,
    )
    contract_reference = f"{'22' * 32}#0"
    script_reference = f"{'66' * 32}#0"
    return {
        contract_reference: redemption.ChainUtxo(
            reference=contract_reference,
            address=str(contract_address),
            lovelace=2_000_000,
            assets=(
                redemption.NativeAssetAmount(
                    redemption.NIGHT_POLICY_ID.payload.hex(),
                    redemption.NIGHT_ASSET_NAME.payload.hex(),
                    70_000_000_007,
                ),
            ),
            is_spent=False,
            has_datum_hash=True,
            has_inline_datum=True,
            has_reference_script=False,
            reference_script_hash=None,
            reference_script_type=None,
        ),
        script_reference: redemption.ChainUtxo(
            reference=script_reference,
            address=str(reference_address),
            lovelace=18_248_540,
            assets=(),
            is_spent=False,
            has_datum_hash=False,
            has_inline_datum=False,
            has_reference_script=True,
            reference_script_hash=redemption.REDEMPTION_SCRIPT_HASH.payload.hex(),
            reference_script_type="plutusV3",
        ),
    }


def transaction_fixture(
    funding: redemption.FundingUtxo,
    *,
    foreign_ada_output: bool = False,
    foreign_collateral_return: bool = False,
    network_id: Network | None = None,
) -> str:
    destination = Address.from_primitive(DESTINATION)
    change = Address.from_primitive(CHANGE_ADDRESS)
    contract_address = Address(
        redemption.REDEMPTION_SCRIPT_HASH,
        destination.staking_part,
        Network.MAINNET,
    )
    foreign_address = Address(
        ScriptHash(bytes.fromhex("55" * 28)),
        None,
        Network.MAINNET,
    )
    outputs = [
        TransactionOutput(
            destination,
            Value(
                2_000_000,
                MultiAsset(
                    {
                        redemption.NIGHT_POLICY_ID: Asset(
                            {redemption.NIGHT_ASSET_NAME: 30_000_000_003}
                        )
                    }
                ),
            ),
        ),
        TransactionOutput(
            contract_address,
            Value(
                2_000_000,
                MultiAsset(
                    {
                        redemption.NIGHT_POLICY_ID: Asset(
                            {redemption.NIGHT_ASSET_NAME: 40_000_000_004}
                        )
                    }
                ),
            ),
            datum=RawPlutusData.from_primitive(0),
            post_alonzo=True,
        ),
        TransactionOutput(change, Value(7_500_000)),
    ]
    if foreign_ada_output:
        outputs.append(TransactionOutput(foreign_address, Value(1_000_000)))

    funding_hash, funding_index = funding.reference.split("#", 1)
    funding_input = TransactionInput(
        TransactionId(bytes.fromhex(funding_hash)), int(funding_index)
    )
    body = TransactionBody(
        inputs=[
            funding_input,
            TransactionInput(TransactionId(bytes.fromhex("22" * 32)), 0),
        ],
        outputs=outputs,
        fee=500_000,
        validity_start=100,
        script_data_hash=ScriptDataHash(bytes.fromhex("77" * 32)),
        collateral=[funding_input],
        collateral_return=TransactionOutput(
            foreign_address if foreign_collateral_return else change,
            Value(9_250_000),
        ),
        total_collateral=750_000,
        reference_inputs=[
            TransactionInput(TransactionId(bytes.fromhex("66" * 32)), 0)
        ],
        network_id=network_id,
    )
    return Transaction(body, TransactionWitnessSet()).to_cbor_hex()


def validated_fixture() -> tuple[
    redemption.FundingUtxo, str, redemption.RedemptionPreview
]:
    funding = funding_fixture()
    transaction_cbor = transaction_fixture(funding)
    key_hash = Address.from_primitive(funding.address).payment_part
    preview = redemption.validate_redemption_transaction(
        transaction_cbor,
        DESTINATION,
        CHANGE_ADDRESS,
        thaw_schedule(),
        [funding],
        {key_hash},
        chain_context(),
    )
    return funding, transaction_cbor, preview


def prepared_fixture() -> redemption.PreparedRedemption:
    funding, transaction_cbor, preview = validated_fixture()
    return redemption.PreparedRedemption(
        destination_address=DESTINATION,
        transaction_cbor=transaction_cbor,
        preview=preview,
        signing_method="Trezor Hardware: test",
        account_index=0,
        scan_limit=20,
        derivation_type="icarus",
        _reference_paths={funding.reference: FUNDING_PATH},
        _key_hash_by_path={
            FUNDING_PATH: Address.from_primitive(funding.address).payment_part,
            CHANGE_PATH: Address.from_primitive(CHANGE_ADDRESS).payment_part,
        },
    )


def test_public_redemption_contract_has_no_host_secret_parameters() -> None:
    parameters = inspect.signature(redemption.RedemptionWorkflow.prepare).parameters
    secret_names = {"seed", "seed_phrase", "mnemonic", "passphrase", "private_key"}
    assert secret_names.isdisjoint(parameters)
    assert secret_names.isdisjoint(redemption.PreparedRedemption.__dataclass_fields__)


def test_schedule_amounts_preserve_night_subunits() -> None:
    schedule = thaw_schedule()
    assert schedule.redeemed == Decimal("30000.000003")
    assert schedule.redeemable_now == Decimal("30000.000003")
    assert Decimal(schedule.total_left_subunits) / 1_000_000 == Decimal(
        "70000.000007"
    )
    assert schedule.total == Decimal("100000.00001")


def test_unknown_thaw_status_is_rejected() -> None:
    with pytest.raises(redemption.ApiError, match="Unknown thaw status"):
        redemption.parse_thaw_schedule(
            {
                "thaws": [
                    {
                        "amount": "1",
                        "status": "unexpected",
                        "thawing_period_start": "now",
                        "transaction_id": None,
                    }
                ]
            }
        )


def test_verified_transaction_matches_expected_redemption() -> None:
    _, transaction_cbor, preview = validated_fixture()
    assert preview.redeemable_night == Decimal("30000.000003")
    assert preview.fee_ada == Decimal("0.5")
    assert preview.total_collateral_ada == Decimal("0.75")
    assert preview.collateral_return_ada == Decimal("9.25")
    assert len(preview.transaction_id) == 64
    assert preview.transaction_id == redemption._exact_transaction_body_hash(
        transaction_cbor
    ).hex()
    assert preview.transaction_id != Transaction.from_cbor(
        transaction_cbor
    ).transaction_body.hash().hex()


def test_funding_selection_minimizes_ada_exposure() -> None:
    template = funding_fixture()
    candidates = [
        replace(template, reference=f"{'12' * 32}#0", lovelace=80_000_000),
        replace(template, reference=f"{'13' * 32}#0", lovelace=2_000_000),
        replace(template, reference=f"{'14' * 32}#0", lovelace=2_600_000),
        replace(template, reference=f"{'15' * 32}#0", lovelace=5_000_000),
    ]
    selected = redemption.select_funding_utxos(candidates)
    assert sum(utxo.lovelace for utxo in selected) == 4_600_000
    assert {utxo.reference for utxo in selected} == {
        f"{'13' * 32}#0",
        f"{'14' * 32}#0",
    }


def test_empty_funding_error_confirms_destination_wallet_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    derivation_calls: list[tuple[int, int, str, str]] = []
    destination_path = "m/1852'/1815'/0'/0/7"

    def fake_derive_base_addresses(
        account_index: int,
        scan_limit: int,
        derivation_type: str,
        *,
        verification_address: str,
    ) -> trezor_signer.TrezorWalletSnapshot:
        derivation_calls.append(
            (account_index, scan_limit, derivation_type, verification_address)
        )
        verified_destination = trezor_signer.TrezorPublicAddress(
            DESTINATION,
            destination_path,
        )
        return trezor_signer.TrezorWalletSnapshot(
            addresses=(
                verified_destination,
                trezor_signer.TrezorPublicAddress(CHANGE_ADDRESS, CHANGE_PATH),
            ),
            verified_destination=verified_destination,
            label="Test Trezor",
            model="T3T1",
            firmware="2.8.10",
        )

    class ScheduleClient:
        def get_schedule(self, destination_address: str) -> redemption.ThawSchedule:
            assert destination_address == DESTINATION
            return thaw_schedule()

    class EmptyKoiosClient:
        def get_address_utxos(
            self,
            addresses: list[str],
        ) -> tuple[redemption.ChainUtxo, ...]:
            assert DESTINATION in addresses
            return ()

    monkeypatch.setattr(
        redemption,
        "derive_base_addresses",
        fake_derive_base_addresses,
    )
    workflow = redemption.RedemptionWorkflow(
        midnight_client=ScheduleClient(),  # type: ignore[arg-type]
        koios_client=EmptyKoiosClient(),  # type: ignore[arg-type]
    )

    with pytest.raises(
        redemption.TransactionValidationError,
        match="Passphrase-Wallet kryptografisch.*0 ADA available",
    ):
        workflow.prepare(DESTINATION, 0, 20, "icarus")

    assert derivation_calls == [(0, 20, "icarus", DESTINATION)]


def test_foreign_ada_output_is_rejected() -> None:
    funding = funding_fixture()
    with pytest.raises(
        redemption.TransactionValidationError,
        match="Unexpected continuation/output",
    ):
        redemption.validate_redemption_transaction(
            transaction_fixture(funding, foreign_ada_output=True),
            DESTINATION,
            CHANGE_ADDRESS,
            thaw_schedule(),
            [funding],
            {Address.from_primitive(funding.address).payment_part},
            chain_context(),
        )


def test_foreign_collateral_return_is_rejected() -> None:
    funding = funding_fixture()
    with pytest.raises(
        redemption.TransactionValidationError,
        match="Collateral return",
    ):
        redemption.validate_redemption_transaction(
            transaction_fixture(funding, foreign_collateral_return=True),
            DESTINATION,
            CHANGE_ADDRESS,
            thaw_schedule(),
            [funding],
            {Address.from_primitive(funding.address).payment_part},
            chain_context(),
        )


def test_wrong_contract_night_balance_is_rejected() -> None:
    funding = funding_fixture()
    context = chain_context()
    contract_reference = f"{'22' * 32}#0"
    context[contract_reference] = replace(
        context[contract_reference],
        assets=(
            redemption.NativeAssetAmount(
                redemption.NIGHT_POLICY_ID.payload.hex(),
                redemption.NIGHT_ASSET_NAME.payload.hex(),
                1,
            ),
        ),
    )
    with pytest.raises(redemption.TransactionValidationError, match="does not contain"):
        redemption.validate_redemption_transaction(
            transaction_fixture(funding),
            DESTINATION,
            CHANGE_ADDRESS,
            thaw_schedule(),
            [funding],
            {Address.from_primitive(funding.address).payment_part},
            context,
        )


def test_prepared_transaction_delegates_once_to_trezor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = prepared_fixture()
    calls: list[dict[str, object]] = []

    def fake_create_witness_set(**kwargs: object) -> str:
        calls.append(kwargs)
        return "a10080"

    monkeypatch.setattr(redemption, "create_trezor_witness_set", fake_create_witness_set)
    assert prepared.create_witness_set() == "a10080"
    assert calls[0]["expected_transaction_id"] == prepared.preview.transaction_id
    with pytest.raises(redemption.RedemptionError, match="already used"):
        prepared.create_witness_set()


def test_submit_rejects_mismatched_transaction_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = prepared_fixture()
    monkeypatch.setattr(
        redemption.PreparedRedemption,
        "create_witness_set",
        lambda _self: "a10080",
    )

    class WrongIdMidnightClient:
        def submit_transaction(self, *_args: object) -> dict[str, object]:
            return {
                "transaction_id": "00" * 32,
                "estimated_submission_time": 10,
            }

    workflow = redemption.RedemptionWorkflow(
        midnight_client=WrongIdMidnightClient(),  # type: ignore[arg-type]
        koios_client=object(),  # type: ignore[arg-type]
    )
    with pytest.raises(redemption.RedemptionError, match="different transaction ID"):
        workflow.submit(prepared)


def test_exact_plutus_transaction_is_mapped_for_trezor() -> None:
    funding, transaction_cbor, _ = validated_fixture()
    request = trezor_signer.build_signing_request(
        transaction_cbor,
        {funding.reference: FUNDING_PATH},
        {
            FUNDING_PATH: Address.from_primitive(FUNDING_ADDRESS).payment_part,
            CHANGE_PATH: Address.from_primitive(CHANGE_ADDRESS).payment_part,
        },
        CHANGE_ADDRESS,
        0,
        "icarus",
    )
    assert request.signing_mode == trezor_messages.CardanoTxSigningMode.PLUTUS_TRANSACTION
    assert len(request.inputs) == 2
    assert request.inputs[0][1]
    assert request.inputs[1][1] == []
    assert [item[0].format for item in request.outputs] == [
        trezor_messages.CardanoTxOutputSerializationFormat.ARRAY_LEGACY,
        trezor_messages.CardanoTxOutputSerializationFormat.MAP_BABBAGE,
        trezor_messages.CardanoTxOutputSerializationFormat.ARRAY_LEGACY,
    ]
    assert b"".join(chunk.data for chunk in request.outputs[1][2]) == b"\x00"
    assert len(request.collateral_inputs) == 1
    assert request.collateral_return is not None
    assert request.total_collateral == 750_000
    assert len(request.reference_inputs) == 1
    assert request.tag_cbor_sets is False


def test_returned_trezor_witness_is_verified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    funding, transaction_cbor, preview = validated_fixture()
    signing_key = SigningKey(bytes(range(32)))
    public_key = bytes(signing_key.verify_key)
    expected_key_hash = PaymentVerificationKey.from_primitive(public_key).hash()
    key_hash_by_path = {
        FUNDING_PATH: expected_key_hash,
        CHANGE_PATH: Address.from_primitive(CHANGE_ADDRESS).payment_part,
    }

    def fake_sign_on_device(_request: trezor_signer.TrezorSigningRequest):
        body_hash = bytes.fromhex(preview.transaction_id)
        return {
            "tx_hash": body_hash,
            "witnesses": [
                {
                    "type": trezor_messages.CardanoTxWitnessType.SHELLEY_WITNESS,
                    "pub_key": public_key,
                    "signature": signing_key.sign(body_hash).signature,
                }
            ],
        }

    monkeypatch.setattr(trezor_signer, "_sign_on_device", fake_sign_on_device)
    witness_cbor = trezor_signer.create_witness_set(
        transaction_cbor,
        preview.transaction_id,
        {funding.reference: FUNDING_PATH},
        key_hash_by_path,
        CHANGE_ADDRESS,
        0,
        "icarus",
    )
    witness_set = TransactionWitnessSet.from_cbor(witness_cbor)
    assert witness_set.vkey_witnesses is not None
    assert len(witness_set.vkey_witnesses) == 1


def test_different_device_body_hash_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    funding, transaction_cbor, preview = validated_fixture()
    key_hash_by_path = {
        FUNDING_PATH: Address.from_primitive(FUNDING_ADDRESS).payment_part,
        CHANGE_PATH: Address.from_primitive(CHANGE_ADDRESS).payment_part,
    }
    monkeypatch.setattr(
        trezor_signer,
        "_sign_on_device",
        lambda _request: {"tx_hash": b"\x00" * 32, "witnesses": []},
    )
    with pytest.raises(trezor_signer.TrezorHardwareError, match="different transaction"):
        trezor_signer.create_witness_set(
            transaction_cbor,
            preview.transaction_id,
            {funding.reference: FUNDING_PATH},
            key_hash_by_path,
            CHANGE_ADDRESS,
            0,
            "icarus",
        )


@pytest.mark.parametrize(
    ("passphrase_protection", "capabilities", "expected_setting"),
    [
        (
            True,
            [trezor_messages.Capability.PassphraseEntry],
            PassphraseSetting.ON_DEVICE,
        ),
        (False, [], PassphraseSetting.STANDARD_WALLET),
    ],
)
def test_cardano_session_never_requests_host_passphrase(
    monkeypatch: pytest.MonkeyPatch,
    passphrase_protection: bool,
    capabilities: list[trezor_messages.Capability],
    expected_setting: PassphraseSetting,
) -> None:
    settings: list[tuple[PassphraseSetting, bool]] = []

    class FakeSession:
        is_invalid = False

        def close(self) -> None:
            self.is_invalid = True

    class FakeClient:
        features = SimpleNamespace(
            passphrase_protection=passphrase_protection,
            capabilities=capabilities,
        )

        def ensure_unlocked(self) -> None:
            return None

        def get_session(
            self,
            *,
            passphrase: PassphraseSetting,
            derive_cardano: bool,
        ) -> FakeSession:
            settings.append((passphrase, derive_cardano))
            return FakeSession()

    monkeypatch.setattr(
        trezor_signer,
        "get_default_client",
        lambda *_args, **_kwargs: FakeClient(),
    )

    with trezor_signer._open_cardano_session():
        pass

    assert settings == [(expected_setting, True)]


def test_destination_wallet_match_is_displayed_on_trezor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    display_requests: list[bool] = []
    returned_addresses = iter(
        [
            FUNDING_ADDRESS,
            FUNDING_ADDRESS,
            CHANGE_ADDRESS,
            CHANGE_ADDRESS,
            CHANGE_ADDRESS,
        ]
    )

    @contextmanager
    def fake_open_cardano_session():
        features = SimpleNamespace(
            label="Test Trezor",
            internal_model="T3T1",
            model="T",
            major_version=2,
            minor_version=8,
            patch_version=10,
        )
        yield SimpleNamespace(features=features), object()

    def fake_get_address(
        _session: object,
        _parameters: object,
        *,
        protocol_magic: int,
        network_id: int,
        show_display: bool,
        derivation_type: trezor_messages.CardanoDerivationType,
    ) -> str:
        assert protocol_magic == trezor_signer.MAINNET_PROTOCOL_MAGIC
        assert network_id == trezor_signer.MAINNET_NETWORK_ID
        assert derivation_type == trezor_messages.CardanoDerivationType.ICARUS
        display_requests.append(show_display)
        return next(returned_addresses)

    monkeypatch.setattr(
        trezor_signer,
        "_open_cardano_session",
        fake_open_cardano_session,
    )
    monkeypatch.setattr(trezor_signer.trezor_cardano, "get_address", fake_get_address)

    snapshot = trezor_signer.derive_base_addresses(
        0,
        2,
        "icarus",
        verification_address=FUNDING_ADDRESS,
    )

    assert snapshot.verified_destination.address == FUNDING_ADDRESS
    assert snapshot.verified_destination.derivation_path == FUNDING_PATH
    assert display_requests == [False, True, False, False, False]


def test_wrong_passphrase_wallet_never_reaches_device_address_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    display_requests: list[bool] = []

    @contextmanager
    def fake_open_cardano_session():
        yield SimpleNamespace(features=object()), object()

    def fake_get_address(
        _session: object,
        _parameters: object,
        **kwargs: object,
    ) -> str:
        show_display = kwargs["show_display"]
        assert isinstance(show_display, bool)
        display_requests.append(show_display)
        return CHANGE_ADDRESS

    monkeypatch.setattr(
        trezor_signer,
        "_open_cardano_session",
        fake_open_cardano_session,
    )
    monkeypatch.setattr(trezor_signer.trezor_cardano, "get_address", fake_get_address)

    with pytest.raises(
        trezor_signer.TrezorHardwareError,
        match="Passphrase-Wallet passt nicht",
    ):
        trezor_signer.derive_base_addresses(
            0,
            2,
            "icarus",
            verification_address=FUNDING_ADDRESS,
        )

    assert display_requests == [False, False, False, False]


def test_device_must_display_the_verified_destination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    returned_addresses = iter([FUNDING_ADDRESS, CHANGE_ADDRESS])

    @contextmanager
    def fake_open_cardano_session():
        yield SimpleNamespace(features=object()), object()

    monkeypatch.setattr(
        trezor_signer,
        "_open_cardano_session",
        fake_open_cardano_session,
    )
    monkeypatch.setattr(
        trezor_signer.trezor_cardano,
        "get_address",
        lambda *_args, **_kwargs: next(returned_addresses),
    )

    with pytest.raises(
        trezor_signer.TrezorHardwareError,
        match="displayed a different address",
    ):
        trezor_signer.derive_base_addresses(
            0,
            1,
            "icarus",
            verification_address=FUNDING_ADDRESS,
        )


def test_passphrase_wallet_without_device_entry_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        features = SimpleNamespace(
            passphrase_protection=True,
            capabilities=[trezor_messages.Capability.Cardano],
        )

        def ensure_unlocked(self) -> None:
            return None

    monkeypatch.setattr(
        trezor_signer,
        "get_default_client",
        lambda *_args, **_kwargs: FakeClient(),
    )

    with pytest.raises(
        trezor_signer.TrezorHardwareError,
        match="cannot accept the passphrase on-device",
    ):
        with trezor_signer._open_cardano_session():
            pass


def test_host_pin_entry_is_rejected() -> None:
    with pytest.raises(
        trezor_signer.TrezorHardwareError,
        match="refuses host-side PIN entry",
    ):
        trezor_signer._reject_host_pin(object())


def test_different_passphrase_wallet_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    funding, transaction_cbor, preview = validated_fixture()
    different_key = SigningKey(bytes(reversed(range(32))))
    body_hash = bytes.fromhex(preview.transaction_id)
    response = {
        "tx_hash": body_hash,
        "witnesses": [
            {
                "type": trezor_messages.CardanoTxWitnessType.SHELLEY_WITNESS,
                "pub_key": bytes(different_key.verify_key),
                "signature": different_key.sign(body_hash).signature,
            }
        ],
    }
    monkeypatch.setattr(
        trezor_signer,
        "_sign_on_device",
        lambda _request: response,
    )

    with pytest.raises(
        trezor_signer.TrezorHardwareError,
        match="passphrase wallet used for signing does not match",
    ):
        trezor_signer.create_witness_set(
            transaction_cbor,
            preview.transaction_id,
            {funding.reference: FUNDING_PATH},
            {
                FUNDING_PATH: Address.from_primitive(FUNDING_ADDRESS).payment_part,
                CHANGE_PATH: Address.from_primitive(CHANGE_ADDRESS).payment_part,
            },
            CHANGE_ADDRESS,
            0,
            "icarus",
        )


def test_invalid_device_signature_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    funding, transaction_cbor, preview = validated_fixture()
    signing_key = SigningKey(bytes(range(32)))
    public_key = bytes(signing_key.verify_key)
    key_hash = PaymentVerificationKey.from_primitive(public_key).hash()
    monkeypatch.setattr(
        trezor_signer,
        "_sign_on_device",
        lambda _request: {
            "tx_hash": bytes.fromhex(preview.transaction_id),
            "witnesses": [
                {
                    "type": trezor_messages.CardanoTxWitnessType.SHELLEY_WITNESS,
                    "pub_key": public_key,
                    "signature": bytes(64),
                }
            ],
        },
    )

    with pytest.raises(
        trezor_signer.TrezorHardwareError,
        match="signature failed local verification",
    ):
        trezor_signer.create_witness_set(
            transaction_cbor,
            preview.transaction_id,
            {funding.reference: FUNDING_PATH},
            {
                FUNDING_PATH: key_hash,
                CHANGE_PATH: Address.from_primitive(CHANGE_ADDRESS).payment_part,
            },
            CHANGE_ADDRESS,
            0,
            "icarus",
        )


def test_incomplete_device_response_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    funding, transaction_cbor, preview = validated_fixture()
    monkeypatch.setattr(
        trezor_signer,
        "_sign_on_device",
        lambda _request: {"witnesses": []},
    )

    with pytest.raises(
        trezor_signer.TrezorHardwareError,
        match="incomplete Cardano signing response",
    ):
        trezor_signer.create_witness_set(
            transaction_cbor,
            preview.transaction_id,
            {funding.reference: FUNDING_PATH},
            {
                FUNDING_PATH: Address.from_primitive(FUNDING_ADDRESS).payment_part,
                CHANGE_PATH: Address.from_primitive(CHANGE_ADDRESS).payment_part,
            },
            CHANGE_ADDRESS,
            0,
            "icarus",
        )


def test_non_mainnet_network_id_is_rejected() -> None:
    funding = funding_fixture()
    with pytest.raises(
        redemption.TransactionValidationError,
        match="non-mainnet network ID",
    ):
        redemption.validate_redemption_transaction(
            transaction_fixture(funding, network_id=Network.TESTNET),
            DESTINATION,
            CHANGE_ADDRESS,
            thaw_schedule(),
            [funding],
            {Address.from_primitive(funding.address).payment_part},
            chain_context(),
        )


def test_midnight_error_details_are_preserved() -> None:
    response = requests.Response()
    response.status_code = 400
    response._content = (
        b'{"info":"next thaw is later","message":"Incorrect build transaction '
        b'request","type":"no_redeemable_thaws"}'
    )

    class FakeSession:
        def request(self, *_args: object, **_kwargs: object) -> requests.Response:
            return response

    client = redemption.MidnightRedemptionClient(FakeSession())  # type: ignore[arg-type]
    with pytest.raises(redemption.ApiError) as context:
        client.get_schedule(DESTINATION)
    assert context.value.error_type == "no_redeemable_thaws"
    assert context.value.info == "next thaw is later"
    assert "Incorrect build transaction request" in str(context.value)
