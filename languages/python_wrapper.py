PYTHON_WRAPPER_TEMPLATE = """
import sys
import json
import traceback
import inspect
import threading

# LeetCode-style prelude: these are available without an import.
from typing import *
import collections, heapq, bisect, math, itertools, functools, string, re, random, operator
from collections import Counter, OrderedDict, defaultdict, deque, namedtuple
from heapq import heapify, heappop, heappush, heappushpop, heapreplace, nlargest, nsmallest
from bisect import bisect, bisect_left, bisect_right, insort, insort_left, insort_right
from functools import cache, cmp_to_key, lru_cache, reduce
from itertools import accumulate, combinations, permutations, product
from math import ceil, comb, floor, gcd, inf, isqrt, log2, sqrt

RESULT_START = "__JUDGE_RESULT_7f3a__"
RESULT_END = "__JUDGE_END_7f3a__"

# ==============================
# Built-in Data Structures
# ==============================

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []


# ==============================
# Helper Builders
# ==============================

def build_tree(values):
    if not values:
        return None

    nodes = [TreeNode(val) if val is not None else None for val in values]
    kids = deque(nodes[1:])

    for node in nodes:
        if node:
            if kids:
                node.left = kids.popleft()
            if kids:
                node.right = kids.popleft()

    return nodes[0]


def tree_to_list(root):
    if not root:
        return []

    result = []
    queue = deque([root])

    while queue:
        node = queue.popleft()
        if node:
            result.append(node.val)
            queue.append(node.left)
            queue.append(node.right)
        else:
            result.append(None)

    while result and result[-1] is None:
        result.pop()

    return result


def build_linked_list(values):
    if not values:
        return None, []

    dummy = ListNode(0)
    curr = dummy
    nodes = []

    for val in values:
        curr.next = ListNode(val)
        curr = curr.next
        nodes.append(curr)

    return dummy.next, nodes


def linked_list_to_list(head):
    result = []
    visited = set()

    while head and head not in visited:
        visited.add(head)
        result.append(head.val)
        head = head.next

    return result


# ==============================
# Graph Support
# ==============================

def build_graph(adjList):
    if not adjList:
        return None

    nodes = {i + 1: Node(i + 1) for i in range(len(adjList))}

    for i, neighbors in enumerate(adjList):
        for neighbor in neighbors:
            nodes[i + 1].neighbors.append(nodes[neighbor])

    return nodes[1]


def graph_to_adjlist(node):
    if not node:
        return []

    visited = set()
    queue = deque([node])
    nodes = []

    while queue:
        curr = queue.popleft()
        if curr in visited:
            continue

        visited.add(curr)
        nodes.append(curr)

        for neighbor in curr.neighbors:
            if neighbor not in visited:
                queue.append(neighbor)

    nodes.sort(key=lambda x: x.val)

    max_val = max(n.val for n in nodes)
    result = [[] for _ in range(max_val)]

    for curr in nodes:
        for neighbor in curr.neighbors:
            result[curr.val - 1].append(neighbor.val)

    return result


# ==============================
# User Code
# ==============================

{source_code}


# ==============================
# Execution Logic
# ==============================

def auto_convert_inputs(test_input):
    converted = {}

    for key, value in test_input.items():

        # ----- Tree -----
        if isinstance(value, list) and key.lower().startswith("root"):
            converted[key] = build_tree(value)

        # ----- Linked List (with optional pos) -----
        elif isinstance(value, list) and key.lower().startswith("head"):

            pos = test_input.get("pos", -1)

            head, nodes = build_linked_list(value)

            # Create cycle if pos is valid
            if pos != -1 and nodes:
                if 0 <= pos < len(nodes):
                    nodes[-1].next = nodes[pos]

            converted[key] = head

        # ----- Graph -----
        elif isinstance(value, list) and key.lower().startswith("adj"):
            converted[key] = build_graph(value)

        # ----- Skip metadata -----
        elif key == "pos":
            continue

        # ----- Multiline string to list (operations format) -----
        elif isinstance(value, str) and chr(10) in value:
            lines = [l.strip() for l in value.strip().split(chr(10)) if l.strip()]
            # Drop leading count line if it is a pure integer
            if lines and lines[0].isdigit():
                lines = lines[1:]
            converted[key] = lines

        else:
            converted[key] = value

    return converted


def auto_convert_output(result):

    if isinstance(result, TreeNode):
        return tree_to_list(result)

    if isinstance(result, ListNode):
        return linked_list_to_list(result)

    if isinstance(result, Node):
        return graph_to_adjlist(result)

    return result


def call_function(func, converted_input):
    sig = inspect.signature(func)
    param_count = len(sig.parameters)
    args = list(converted_input.values())

    if param_count == len(converted_input):
        return func(*args), args

    result = func(**converted_input)
    return result, list(converted_input.values())


def _user_function(function_name):
    # Only functions defined in the submission count, not names that the
    # prelude imported (e.g. heapq.merge for a problem called "merge").
    func = globals().get(function_name)
    if inspect.isfunction(func) and func.__module__ == __name__:
        return func
    return None


def execute_function(function_name, test_input):

    converted_input = auto_convert_inputs(test_input)

    func = None
    if "Solution" in globals() and inspect.isclass(globals()["Solution"]):
        solution_instance = globals()["Solution"]()
        if hasattr(solution_instance, function_name):
            func = getattr(solution_instance, function_name)

    if func is None:
        func = _user_function(function_name)

    if func is None:
        raise Exception(f"Function '{function_name}' not found")

    result, args = call_function(func, converted_input)
    output = {"result": auto_convert_output(result)}
    if result is None and args:
        # In-place problems (e.g. moveZeroes) return nothing; the judge
        # compares the mutated first argument instead.
        output["mutated"] = auto_convert_output(args[0])
    return output


def emit(obj):
    sys.stdout.flush()
    sys.stdout.write(RESULT_START + json.dumps(obj) + RESULT_END + chr(10))
    sys.stdout.flush()


def main():
    exit_code = [0]

    def run():
        try:
            raw_input = sys.stdin.read()
            payload = json.loads(raw_input)

            function_name = payload["function_name"]
            test_input = payload["input"]

            emit(execute_function(function_name, test_input))

        except RecursionError:
            emit({"error": "RecursionError: maximum recursion depth exceeded"})
            exit_code[0] = 1
        except BaseException as e:
            message = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            emit({
                "error": message,
                "trace": traceback.format_exc()
            })
            exit_code[0] = 1

    # Deep recursion (DFS on 10^5 nodes) needs a bigger stack than the default.
    sys.setrecursionlimit(1_000_000)
    threading.stack_size(512 * 1024 * 1024)
    worker = threading.Thread(target=run)
    worker.start()
    worker.join()
    sys.exit(exit_code[0])


if __name__ == "__main__":
    main()

"""
