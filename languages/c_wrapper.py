# Prepended (with gcc -include) to the user's C file: the headers and struct
# definitions LeetCode makes available to C submissions.
C_PRELUDE = r"""
#include <assert.h>
#include <ctype.h>
#include <limits.h>
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct ListNode {
    int val;
    struct ListNode *next;
};

struct TreeNode {
    int val;
    struct TreeNode *left;
    struct TreeNode *right;
};
"""

# C++ harness linked with the compiled user code. The ListNode/TreeNode
# structs in cpp_support.hpp have the same layout as the C ones above.
C_WRAPPER_TEMPLATE = r"""
#include "/opt/cpp_support.hpp"

extern "C" {
__FUNCTION_DECLARATION_PLACEHOLDER__
}

namespace judge_c {

// Strings arrive either as a JSON string or as a list of one-character strings.
inline string charsToString(const json& j) {
    if (!j.is_array()) return j.get<string>();
    string s;
    for (const auto& c : j) s.push_back(judge::Arg<char>::get(c));
    return s;
}

inline json stringToChars(const char* s, int n) {
    json out = json::array();
    for (int i = 0; i < n; ++i) out.push_back(string(1, s[i]));
    return out;
}

// A char** argument: a list of strings, or a grid of characters.
struct CharRows {
    vector<string> rows;
    vector<char*> ptrs;
    vector<int> cols;
    bool grid = false;

    explicit CharRows(const json& j) {
        if (!j.is_array()) {
            rows = judge::Arg<vector<string>>::get(j);
        } else {
            for (const auto& item : j) {
                if (item.is_array()) grid = true;
                rows.push_back(charsToString(item));
            }
        }
        for (auto& r : rows) {
            ptrs.push_back(r.data());
            cols.push_back(static_cast<int>(r.size()));
        }
    }

    json toJson() const {
        json out = json::array();
        for (size_t i = 0; i < rows.size(); ++i) {
            out.push_back(grid ? stringToChars(ptrs[i], cols[i]) : json(string(ptrs[i], cols[i])));
        }
        return out;
    }
};

// An int** argument: a 2D grid of ints.
struct IntRows {
    vector<vector<int>> rows;
    vector<int*> ptrs;
    vector<int> cols;

    explicit IntRows(const json& j) {
        rows = j.get<vector<vector<int>>>();
        for (auto& r : rows) {
            ptrs.push_back(r.data());
            cols.push_back(static_cast<int>(r.size()));
        }
    }
};

}  // namespace judge_c

static json judgeRunOne(const json& testCase) {
    judge::listCyclePos = -1;
    judge::Input _in(testCase, __SKIP_POS_PLACEHOLDER__);

    __PARAMETER_DESERIALIZATION_PLACEHOLDER__

    json _output;
    __CALL_AND_SERIALIZE_PLACEHOLDER__
    return _output;
}

int main() {
    string _stdin_raw((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());

    json _payload;
    try {
        _payload = json::parse(_stdin_raw);
    } catch (...) {
        judge::emitError("Invalid JSON input");
        return 1;
    }

    size_t _index = 0;
    try {
        if (_payload.contains("test_cases")) {
            // One result block per test case, so a crash part-way through
            // still tells the judge which test case failed.
            const json& _cases = _payload["test_cases"];
            for (_index = 0; _index < _cases.size(); ++_index) {
                json _out = judgeRunOne(_cases[_index]);
                _out["index"] = _index;
                judge::emit(_out);
            }
        } else {
            judge::emit(judgeRunOne(_payload));
        }
    } catch (const exception& e) {
        json _error;
        _error["error"] = e.what();
        _error["failed_test_case_index"] = _index;
        judge::emit(_error);
        return 1;
    }

    return 0;
}
"""
