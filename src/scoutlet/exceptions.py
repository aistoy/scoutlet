"""Exception types for scoutlet, ported from SearXNG."""

import typing as t

if t.TYPE_CHECKING:
    from lxml.etree import XPath


class SearchException(Exception):
    """Base exception."""


class SearchEngineException(SearchException):
    """Error inside an engine."""


class SearchEngineResponseException(SearchEngineException):
    """Impossible to parse the result of an engine."""


class SearchEngineAPIException(SearchEngineResponseException):
    """The website has returned an application error."""


class SearchEngineAccessDeniedException(SearchEngineResponseException):
    """The website is blocking the access."""

    DEFAULT_SUSPEND_TIME = 86400  # 1 day

    def __init__(self, suspended_time: int | None = None, message: str = 'Access denied'):
        if suspended_time is None:
            suspended_time = self.DEFAULT_SUSPEND_TIME
        self.message = f"{message} (suspended_time={suspended_time})"
        self.suspended_time = suspended_time
        super().__init__(self.message)


class SearchEngineCaptchaException(SearchEngineAccessDeniedException):
    """The website has returned a CAPTCHA."""

    DEFAULT_SUSPEND_TIME = 86400

    def __init__(self, suspended_time: int | None = None, message: str = 'CAPTCHA'):
        super().__init__(message=message, suspended_time=suspended_time)


class SearchEngineTooManyRequestsException(SearchEngineAccessDeniedException):
    """The website has returned a Too Many Request status code."""

    DEFAULT_SUSPEND_TIME = 3660  # ~1 hour

    def __init__(self, suspended_time: int | None = None, message: str = 'Too many requests'):
        super().__init__(message=message, suspended_time=suspended_time)


class SearchXPathSyntaxException(SearchEngineException):
    """Syntax error in a XPATH."""

    def __init__(self, xpath_spec: "str | XPath", message: str):
        super().__init__(str(xpath_spec) + " " + message)
        self.message = message
        self.xpath_str = str(xpath_spec)


class SearchEngineXPathException(SearchEngineResponseException):
    """Error while getting the result of an XPath expression."""

    def __init__(self, xpath_spec: "str | XPath", message: str):
        super().__init__(str(xpath_spec) + " " + message)
        self.message = message
        self.xpath_str = str(xpath_spec)
