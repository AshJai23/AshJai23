"""Optional process-memory telemetry; absence must never prevent application startup."""
import sys
try:
    import resource as _resource
except ImportError:
    _resource=None

def peak_rss_mib():
    if _resource is None:return None
    try:
        value=_resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss
    except (AttributeError,OSError):return None
    # macOS reports bytes; Linux reports KiB.
    divisor=1024*1024 if sys.platform=='darwin' else 1024
    return round(value/divisor,2)
