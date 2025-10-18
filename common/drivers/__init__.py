"""Common CNC driver package init.

This file exposes the CncDriver abstract base and any provided concrete drivers
so `from common.drivers import CncDriver` works even when importing from
`common.driver` or other modules.

The original file was missing in the working tree; restored minimal contents
based on the backup.
"""
from .base import CncDriver

__all__ = ["CncDriver"]
