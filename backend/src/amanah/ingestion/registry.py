"""Which adapter serves which configured source (B-S8.4).

The registry is the one place that decides "this source key is served by that
implementation", and it is deliberately explicit rather than discovered by
import scanning: a source that nobody registered simply cannot run, which is the
safe direction to fail.

It is also where fixture and live data are kept from substituting for each other.
An adapter declares `is_fixture`, the registry refuses to serve a live source
with a fixture adapter, and every item the adapter produces carries the flag
onward. `AGENTS.md` requires fixture and live to stay distinguishable from
storage through to the screen; this is where that starts.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from amanah.ingestion.configuration import SeedConfiguration, SourceConfiguration
from amanah.ingestion.contract import SourceAdapter
from amanah.settings import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AdapterContext:
    """Everything an adapter may be built from.

    A single value rather than four parameters because adapters need different
    subsets of it: the provider-backed ones read settings and configuration, and
    the user-submission adapter also needs the worker's session, because the
    queue of submissions people made is what that source discovers.
    """

    session: Session
    settings: Settings
    sources: SourceConfiguration
    seeds: SeedConfiguration


#: Builds one adapter from that context. A factory rather than an instance, so an
#: adapter is constructed only when a run actually needs it and can read the
#: configuration current at that moment.
type AdapterFactory = Callable[[AdapterContext], SourceAdapter]


class UnknownSourceError(LookupError):
    """No adapter is registered for that source key."""


class SourceDisabledError(RuntimeError):
    """The source exists but is not enabled for collection."""


@dataclass(frozen=True, slots=True)
class Registration:
    """One registered adapter."""

    source_key: str
    factory: AdapterFactory
    is_fixture: bool


class AdapterRegistry:
    """Resolves a configured source key to a usable adapter."""

    def __init__(self) -> None:
        self._registrations: dict[str, Registration] = {}

    def register(self, source_key: str, factory: AdapterFactory, *, is_fixture: bool) -> None:
        if source_key in self._registrations:
            raise ValueError(f"an adapter is already registered for {source_key}")
        self._registrations[source_key] = Registration(
            source_key=source_key, factory=factory, is_fixture=is_fixture
        )

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._registrations))

    def build(self, source_key: str, context: AdapterContext) -> SourceAdapter:
        """Construct the adapter for one source, or refuse.

        The fixture check is the point of doing this here rather than at the call
        site: a source configured as live must not be served by an adapter that
        invents its data, however convenient that would be in a demo.
        """
        registration = self._registrations.get(source_key)
        if registration is None:
            raise UnknownSourceError(source_key)
        configured = context.sources.by_key(source_key)
        if configured is None:
            raise UnknownSourceError(source_key)

        adapter = registration.factory(context)
        if adapter.is_fixture != registration.is_fixture:
            raise RuntimeError(
                f"adapter for {source_key} disagrees with its registration about fixture status"
            )
        return adapter


def build_default_registry(sources: SourceConfiguration) -> AdapterRegistry:
    """The adapters this service ships with, for one reviewed catalogue.

    News outlets are registered from configuration rather than from a list in
    code, so adding a reviewed outlet is a configuration change. The direction
    only goes one way: an outlet that is not in configuration cannot run, because
    there is nothing to register it from.

    Imports are local so registering an adapter cannot create an import cycle
    back through the pipeline that uses it.
    """
    from amanah.contributions.submissions import USER_SUBMISSION_SOURCE_KEY
    from amanah.ingestion.fixtures.adapter import FIXTURE_SOURCE_KEY, FixtureAdapter
    from amanah.ingestion.news.adapter import news_source_keys
    from amanah.ingestion.urls.adapter import build_user_submission_adapter
    from amanah.ingestion.youtube.adapter import YOUTUBE_SOURCE_KEY, build_youtube_adapter

    registry = AdapterRegistry()
    registry.register(
        FIXTURE_SOURCE_KEY,
        lambda context: FixtureAdapter(),
        is_fixture=True,
    )
    registry.register(
        YOUTUBE_SOURCE_KEY,
        lambda context: build_youtube_adapter(context.settings, context.sources, context.seeds),
        is_fixture=False,
    )
    registry.register(
        USER_SUBMISSION_SOURCE_KEY,
        lambda context: build_user_submission_adapter(context.session, context.settings),
        is_fixture=False,
    )
    for source_key in news_source_keys(sources):
        registry.register(source_key, _news_factory(source_key), is_fixture=False)
    return registry


def _news_factory(source_key: str) -> AdapterFactory:
    def factory(context: AdapterContext) -> SourceAdapter:
        from amanah.ingestion.news.adapter import build_news_adapter

        return build_news_adapter(source_key, context.settings, context.sources, context.seeds)

    return factory
