from enum import IntEnum


class ErrorCode(IntEnum):
    SUCCESS = 0
    BAD_REQUEST = 40000
    UNAUTHORIZED = 40100
    FORBIDDEN = 40300
    NOT_FOUND = 40400
    VALIDATION_ERROR = 42200
    RATE_LIMITED = 42900
    LLM_CALL_FAILED = 50002
    TOOL_CALL_FAILED = 50004
    STRUCTURED_OUTPUT_PARSE_FAILED = 50016
    INTERNAL_ERROR = 50000


class AppException(Exception):
    def __init__(
        self, message, code=ErrorCode.INTERNAL_ERROR, status_code=500, data=None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.data = data or {}
        super().__init__(message)
