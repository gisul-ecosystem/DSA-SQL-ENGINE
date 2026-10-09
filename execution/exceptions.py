class CompileError(Exception):
    """Raised when compilation fails."""
    pass


class RuntimeExecutionError(Exception):
    """Raised when user code crashes during execution."""

    def __init__(self, message: str = "Runtime error", failed_test_case_index: int | None = None):
        super().__init__(message)
        self.failed_test_case_index = failed_test_case_index


class ExecutionTimeoutError(RuntimeExecutionError):
    """Raised when execution exceeds time limit."""

    def __init__(self, message: str = "Time limit exceeded", failed_test_case_index: int | None = None):
        super().__init__(message, failed_test_case_index)
