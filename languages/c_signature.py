"""
Find a function definition in C or C++ source and split its signature.

Used by the C and C++ executors to generate the code that reads each
argument from JSON and calls the user's function.
"""

import re
from dataclasses import dataclass

from execution.exceptions import CompileError

_RETURN_TYPE_KEYWORDS = {"static", "inline", "virtual", "constexpr", "extern", "friend", "explicit"}
_TRAILING_QUALIFIERS = re.compile(r"\s*(?:(?:const|noexcept|override|final)\b|&&|&|\s)*")


@dataclass
class Param:
    type: str      # e.g. "vector<int>&", "struct ListNode*", "int"
    name: str      # e.g. "nums"
    raw: str       # the parameter as written


@dataclass
class Signature:
    return_type: str
    params: list[Param]
    raw_params: str          # the parameter list as written, for forward declarations
    in_solution_class: bool  # defined inside `class Solution` / `struct Solution`


def strip_comments(code: str) -> str:
    """Remove comments and blank out string/char literals, keeping offsets stable."""
    out = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        nxt = code[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            while i < n and code[i] != "\n":
                out.append(" ")
                i += 1
        elif c == "/" and nxt == "*":
            end = code.find("*/", i + 2)
            end = n if end == -1 else end + 2
            out.append(re.sub(r"[^\n]", " ", code[i:end]))
            i = end
        elif c in "\"'":
            quote = c
            out.append(c)
            i += 1
            while i < n and code[i] != quote:
                if code[i] == "\\" and i + 1 < n:
                    out.append("  ")
                    i += 2
                    continue
                out.append(" " if code[i] != "\n" else "\n")
                i += 1
            if i < n:
                out.append(quote)
                i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def split_top_level(text: str, sep: str = ",") -> list[str]:
    parts, depth, current = [], 0, []
    for ch in text:
        if ch in "<([{":
            depth += 1
        elif ch in ">)]}":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _matching_paren(code: str, open_index: int) -> int:
    depth = 0
    for i in range(open_index, len(code)):
        if code[i] == "(":
            depth += 1
        elif code[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _return_type_before(code: str, name_index: int) -> str:
    i = name_index - 1
    while i >= 0:
        c = code[i]
        if c in ";{}#":
            break
        if c == ":" and not (i > 0 and code[i - 1] == ":") and not (i + 1 < len(code) and code[i + 1] == ":"):
            break  # "public:" label, not "std::"
        i -= 1
    words = code[i + 1:name_index].split()
    words = [w for w in words if w not in _RETURN_TYPE_KEYWORDS and not w.startswith("[[")]
    # "Solution::twoSum" style out-of-class definitions
    text = " ".join(words)
    return re.sub(r"\bSolution\s*::\s*$", "", text).strip()


def _parse_param(raw: str) -> Param:
    text = raw.split("=", 1)[0].strip()  # drop default values
    match = re.match(r"^(.*?)([A-Za-z_]\w*)\s*((?:\[[^\]]*\])*)$", text, re.DOTALL)
    if not match or not match.group(1).strip():
        raise CompileError(f"Could not parse parameter: {raw}")
    type_text, name, array_suffix = match.groups()
    type_text = " ".join(type_text.split())
    type_text = re.sub(r"\s*([*&])\s*", r"\1", type_text)
    if array_suffix:
        type_text += "*" * array_suffix.count("[")
    return Param(type=type_text, name=name, raw=raw.strip())


def parse_signature(code: str, function_name: str) -> Signature:
    clean = strip_comments(code)
    for match in re.finditer(rf"\b{re.escape(function_name)}\s*\(", clean):
        open_index = match.end() - 1
        close_index = _matching_paren(clean, open_index)
        if close_index == -1:
            continue
        after = _TRAILING_QUALIFIERS.match(clean, close_index + 1).end()
        if after >= len(clean) or clean[after] != "{":
            continue  # a call or a declaration, not the definition

        return_type = _return_type_before(clean, match.start())
        if not return_type:
            continue  # constructor-like or a call such as `return f(x) {`

        raw_params = code[open_index + 1:close_index].strip()
        clean_params = clean[open_index + 1:close_index].strip()
        params = []
        if clean_params and clean_params != "void":
            raws = split_top_level(raw_params)
            for raw in raws:
                params.append(_parse_param(raw))

        class_match = re.search(r"\b(class|struct)\s+Solution\b[^;{]*\{", clean)
        in_class = bool(class_match) and class_match.start() < match.start()
        return Signature(return_type, params, raw_params, in_class)

    raise CompileError(f"Could not find a definition of function '{function_name}'")
