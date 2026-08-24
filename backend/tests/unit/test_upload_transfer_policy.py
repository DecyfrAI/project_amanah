"""Whether uploaded pixels may be sent to the model provider (B-S28.4).

An upload is not this product's material. Nobody reviewed it before it arrived,
no source licence covers it, and it may contain a face or a private conversation.
So it is refused by default and a deployment opts in deliberately.
"""

from __future__ import annotations

from amanah.domain.enums import PublicPlatform, RetentionPolicy
from amanah.ml.policy import DataClass, TransferRequest, authorize_transfer


def _upload(*, allow: bool, is_fixture: bool = False) -> TransferRequest:
    return TransferRequest(
        data_class=DataClass.user_submitted_media,
        platform=PublicPlatform.not_applicable,
        retention_policy=RetentionPolicy.indefinite_permitted,
        is_fixture=is_fixture,
        allow_third_party_content_inference=allow,
    )


def test_uploaded_media_is_refused_by_default() -> None:
    decision = authorize_transfer(_upload(allow=False))

    assert not decision.is_permitted
    assert decision.reason == "third_party_content_inference_disabled"


def test_uploaded_media_is_permitted_once_the_deployment_opts_in() -> None:
    assert authorize_transfer(_upload(allow=True)).is_permitted


def test_the_fixture_flag_does_not_bypass_the_opt_in() -> None:
    """A caller cannot relabel someone's upload as this product's own material."""
    decision = authorize_transfer(_upload(allow=False, is_fixture=True))

    assert not decision.is_permitted
    assert decision.reason == "third_party_content_inference_disabled"


def test_the_catalogue_is_unaffected_by_the_upload_gate() -> None:
    """Reviewed corpus images keep working with the opt-in off."""
    catalogue = TransferRequest(
        data_class=DataClass.collected_text,
        platform=PublicPlatform.not_applicable,
        retention_policy=RetentionPolicy.indefinite_permitted,
        is_fixture=True,
        allow_third_party_content_inference=False,
    )

    assert authorize_transfer(catalogue).is_permitted


def test_the_reason_is_a_stable_code_rather_than_a_sentence() -> None:
    reason = authorize_transfer(_upload(allow=False)).reason

    assert reason is not None
    assert " " not in reason
