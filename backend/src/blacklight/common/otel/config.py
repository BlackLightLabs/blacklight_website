"""
OpenTelemetry SDK Configuration

Sets up OpenTelemetry metrics and tracing with configurable exporters.

Supported Exporters:
- Console: Debug output to console
- OTLP: OpenTelemetry Protocol (for Jaeger, Tempo, Honeycomb, etc.)
- Prometheus: Prometheus-compatible metrics endpoint
- Jaeger: Direct Jaeger tracing export

Usage:
    from src.blacklight.common.otel.config import setup_telemetry

    setup_telemetry()  # Uses settings from environment
"""

import structlog
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    ParentBasedTraceIdRatioBased,
    TraceIdRatioBased,
)
from prometheus_client import REGISTRY

from src.blacklight.common.settings import settings

logger = structlog.get_logger("blacklight.otel")

# Global telemetry components
_meter_provider: MeterProvider | None = None
_tracer_provider: TracerProvider | None = None


def get_resource() -> Resource:
    """
    Create OpenTelemetry Resource with service metadata.

    Resource attributes identify the service in telemetry backends.
    """
    return Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": settings.otel_service_version,
            "deployment.environment": settings.otel_environment,
        }
    )


def create_metrics_exporter() -> PeriodicExportingMetricReader | PrometheusMetricReader | None:
    """
    Create metrics exporter based on configuration.

    Returns:
        Metric reader for MeterProvider, or None if metrics disabled
    """
    exporter_type = settings.otel_metrics_exporter.lower()

    if exporter_type == "none":
        logger.info("metrics_exporter_disabled")
        return None

    elif exporter_type == "console":
        logger.info("metrics_exporter_configured", exporter="console")
        return PeriodicExportingMetricReader(
            exporter=ConsoleMetricExporter(),
            export_interval_millis=60000,  # Export every 60 seconds
        )

    elif exporter_type == "otlp":
        logger.info(
            "metrics_exporter_configured",
            exporter="otlp",
            endpoint=settings.otel_otlp_endpoint,
        )
        headers = {}
        if settings.otel_otlp_headers:
            for header in settings.otel_otlp_headers.split(","):
                key, value = header.split("=", 1)
                headers[key.strip()] = value.strip()

        return PeriodicExportingMetricReader(
            exporter=OTLPMetricExporter(
                endpoint=settings.otel_otlp_endpoint,
                insecure=settings.otel_otlp_insecure,
                headers=headers if headers else None,
            ),
            export_interval_millis=60000,  # Export every 60 seconds
        )

    elif exporter_type == "prometheus":
        logger.info(
            "metrics_exporter_configured",
            exporter="prometheus",
            port=settings.otel_prometheus_port,
        )
        # PrometheusMetricReader uses the global prometheus_client REGISTRY
        # and serves metrics via a separate HTTP endpoint
        return PrometheusMetricReader(registry=REGISTRY)

    else:
        logger.warning(
            "unknown_metrics_exporter",
            exporter=exporter_type,
            message="Falling back to console exporter",
        )
        return PeriodicExportingMetricReader(
            exporter=ConsoleMetricExporter(),
            export_interval_millis=60000,
        )


def create_trace_sampler():
    """
    Create trace sampler based on configuration.

    Returns:
        Sampler instance for TracerProvider
    """
    sampler_type = settings.otel_traces_sampler.lower()

    if sampler_type == "always_on":
        return ALWAYS_ON
    elif sampler_type == "always_off":
        return ALWAYS_OFF
    elif sampler_type == "traceidratio":
        return TraceIdRatioBased(settings.otel_traces_sampler_arg)
    elif sampler_type == "parentbased_always_on":
        return ParentBasedTraceIdRatioBased(ALWAYS_ON)
    else:
        logger.warning(
            "unknown_trace_sampler",
            sampler=sampler_type,
            message="Falling back to always_on",
        )
        return ALWAYS_ON


def create_trace_exporter() -> BatchSpanProcessor | None:
    """
    Create trace exporter based on configuration.

    Returns:
        BatchSpanProcessor for TracerProvider, or None if tracing disabled
    """
    exporter_type = settings.otel_traces_exporter.lower()

    if exporter_type == "none":
        logger.info("trace_exporter_disabled")
        return None

    elif exporter_type == "console":
        logger.info("trace_exporter_configured", exporter="console")
        return BatchSpanProcessor(ConsoleSpanExporter())

    elif exporter_type == "otlp":
        logger.info(
            "trace_exporter_configured",
            exporter="otlp",
            endpoint=settings.otel_otlp_endpoint,
        )
        headers = {}
        if settings.otel_otlp_headers:
            for header in settings.otel_otlp_headers.split(","):
                key, value = header.split("=", 1)
                headers[key.strip()] = value.strip()

        return BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.otel_otlp_endpoint,
                insecure=settings.otel_otlp_insecure,
                headers=headers if headers else None,
            )
        )

    elif exporter_type == "jaeger":
        logger.warning(
            "jaeger_exporter_deprecated",
            message="Jaeger now supports OTLP. Use OTEL_TRACES_EXPORTER=otlp instead",
        )
        # Fallback to OTLP for Jaeger
        return BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.otel_otlp_endpoint,
                insecure=settings.otel_otlp_insecure,
            )
        )

    else:
        logger.warning(
            "unknown_trace_exporter",
            exporter=exporter_type,
            message="Falling back to console exporter",
        )
        return BatchSpanProcessor(ConsoleSpanExporter())


def setup_telemetry() -> None:
    """
    Set up OpenTelemetry metrics and tracing.

    Call this once at application startup to initialize the global
    MeterProvider and TracerProvider.

    Example:
        from src.blacklight.common.otel.config import setup_telemetry

        setup_telemetry()
    """
    global _meter_provider, _tracer_provider

    if not settings.otel_enabled:
        logger.info("opentelemetry_disabled")
        return

    logger.info(
        "initializing_opentelemetry",
        service_name=settings.otel_service_name,
        environment=settings.otel_environment,
        metrics_exporter=settings.otel_metrics_exporter,
        traces_exporter=settings.otel_traces_exporter,
    )

    resource = get_resource()

    # Set up Metrics
    metric_reader = create_metrics_exporter()
    if metric_reader:
        _meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader],
        )
        metrics.set_meter_provider(_meter_provider)
        logger.info("metrics_provider_initialized", exporter=settings.otel_metrics_exporter)

    # Set up Tracing
    trace_processor = create_trace_exporter()
    if trace_processor:
        sampler = create_trace_sampler()
        _tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler,
        )
        _tracer_provider.add_span_processor(trace_processor)
        trace.set_tracer_provider(_tracer_provider)
        logger.info(
            "trace_provider_initialized",
            exporter=settings.otel_traces_exporter,
            sampler=settings.otel_traces_sampler,
        )

    logger.info("opentelemetry_initialized_successfully")


def get_meter_provider() -> MeterProvider | None:
    """Get the global MeterProvider instance."""
    return _meter_provider


def get_tracer_provider() -> TracerProvider | None:
    """Get the global TracerProvider instance."""
    return _tracer_provider


def shutdown_telemetry() -> None:
    """
    Shut down telemetry providers and flush pending data.

    Call this on application shutdown to ensure all telemetry data is exported.
    """
    global _meter_provider, _tracer_provider

    logger.info("shutting_down_opentelemetry")

    if _meter_provider:
        _meter_provider.shutdown()
        logger.info("meter_provider_shutdown")

    if _tracer_provider:
        _tracer_provider.shutdown()
        logger.info("tracer_provider_shutdown")

    logger.info("opentelemetry_shutdown_complete")
