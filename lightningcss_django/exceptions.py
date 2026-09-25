"""Exceptions raised by lightningcss-django."""


class CssModuleError(Exception):
    """Base class for all lightningcss-django errors."""


class CssModuleNotFoundError(CssModuleError, KeyError):
    """A requested ``*.module.css`` file could not be located."""


class CompileError(CssModuleError):
    """Lightning CSS failed to compile a stylesheet."""
