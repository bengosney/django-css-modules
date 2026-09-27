"""Exceptions raised by django-css-modules."""


class CssModuleError(Exception):
    """Base class for all django-css-modules errors."""


class CssModuleNotFoundError(CssModuleError, KeyError):
    """A requested ``*.module.css`` file could not be located."""


class CompileError(CssModuleError):
    """Lightning CSS failed to compile a stylesheet."""
