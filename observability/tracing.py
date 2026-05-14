import os
from contextlib import contextmanager

from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode


_CONFIGURED = False


def configure_tracing(service_name: str) -> None:
    global _CONFIGURED
    if _CONFIGURED or os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4318")
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces"))
    )
    trace.set_tracer_provider(provider)
    _CONFIGURED = True


def instrument_fastapi(app, service_name: str) -> None:
    configure_tracing(service_name)
    FastAPIInstrumentor.instrument_app(app)


def tracer():
    return trace.get_tracer("execution-engine")


def inject_context(payload: dict) -> dict:
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    if carrier:
        payload["_trace_context"] = carrier
    return payload


def extract_context(payload: dict):
    return propagate.extract(payload.get("_trace_context") or {})


@contextmanager
def span(name: str, *, attributes: dict | None = None, context=None, kind=SpanKind.INTERNAL):
    with tracer().start_as_current_span(
        name,
        context=context,
        kind=kind,
        attributes=attributes or {},
    ) as current_span:
        try:
            yield current_span
        except Exception as exc:
            current_span.record_exception(exc)
            current_span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
