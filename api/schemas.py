from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional, Union


# -------------------------
# Base Config (Strict Mode)
# -------------------------

class StrictBaseModel(BaseModel):
    class Config:
        extra = "forbid"


# -------------------------
# Test Case Model
# -------------------------

class TestCase(StrictBaseModel):
    input: Dict[str, Any]
    expected_output: Any


# -------------------------
# Execute Request Model
# -------------------------

class ExecuteRequest(StrictBaseModel):
    language: Literal[
        "python",
        "javascript",
        "c",
        "java",
        "kotlin",
        "go",
        "rust",
        "typescript",
        "cpp",
        "csharp",
    ]

    source_code: str = Field(..., min_length=1, max_length=50000)

    function_name: str = Field(..., min_length=1, max_length=100)

    test_cases: List[TestCase] = Field(
        ...,
        min_length=1,
        max_length=20,
    )

    # Whether a function that returns nothing is judged on its mutated first
    # argument (LeetCode in-place problems such as moveZeroes). None: decide
    # from the code (void/Unit/() in typed languages, a None/undefined return
    # in Python/JS/TS). Callers that know the problem's return type should set it.
    in_place: Optional[bool] = None


# -------------------------
# Execution Result Models
# -------------------------

class AcceptedResponse(StrictBaseModel):
    verdict: Literal["accepted"]
    actual_outputs: List[Any]


class WrongAnswerResponse(StrictBaseModel):
    verdict: Literal["wrong_answer"]
    failed_test_case_index: int = Field(..., ge=0)
    actual_output: Any
    expected_output: Any
    # Outputs of the test cases that passed before the failing one.
    actual_outputs: List[Any] = Field(default_factory=list)


class RuntimeErrorResponse(StrictBaseModel):
    verdict: Literal["runtime_error"]
    failed_test_case_index: int = Field(..., ge=0)
    error_message: str = Field(..., max_length=1000)
    # Outputs of the test cases that passed before the failing one (empty when
    # the language runs all test cases in one batch).
    actual_outputs: List[Any] = Field(default_factory=list)


class CompilationErrorResponse(StrictBaseModel):
    verdict: Literal["compilation_error"]
    error_message: str = Field(..., max_length=1000)


class TimeoutResponse(StrictBaseModel):
    verdict: Literal["timeout"]
    failed_test_case_index: int = Field(..., ge=0)
    actual_outputs: List[Any] = Field(default_factory=list)


class ErrorResponse(StrictBaseModel):
    verdict: Literal["error"]
    error_message: str


ExecuteResponse = Union[
    AcceptedResponse,
    WrongAnswerResponse,
    RuntimeErrorResponse,
    CompilationErrorResponse,
    TimeoutResponse,
    ErrorResponse,
]


# -------------------------
# Raw Execute Request Model
# -------------------------

class RawExecuteRequest(StrictBaseModel):
    language: Literal[
        "python",
        "javascript",
        "c",
        "java",
        "kotlin",
        "go",
        "rust",
        "typescript",
        "cpp",
        "csharp",
    ]
    source_code: str = Field(..., min_length=1, max_length=50000)
    stdin: str = Field("", max_length=10000)
    args: List[str] = Field(default_factory=list, max_length=100)


class RawExecuteResponse(StrictBaseModel):
    stdout: str
    stderr: str
    exit_code: int
