"""
互換性維持のためのラッパ。新しいコードは ``common.drivers`` を参照。
"""

from common.drivers import CncDriver

__all__ = ["CncDriver"]
