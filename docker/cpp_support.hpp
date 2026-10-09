// Support code for judged C++ submissions. Precompiled into the image
// (docker/cpp.Dockerfile), so keep it stable: every change needs an image rebuild.
#include <bits/stdc++.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;
using namespace std;

// LeetCode definitions.
struct ListNode {
    int val;
    ListNode* next;
    ListNode() : val(0), next(nullptr) {}
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode* next) : val(x), next(next) {}
};

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode() : val(0), left(nullptr), right(nullptr) {}
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
    TreeNode(int x, TreeNode* left, TreeNode* right) : val(x), left(left), right(right) {}
};

namespace judge {

inline const char* RESULT_START = "__JUDGE_RESULT_7f3a__";
inline const char* RESULT_END = "__JUDGE_END_7f3a__";

// Index of the node the tail links back to (LeetCode "pos"), -1 for none.
inline int listCyclePos = -1;

inline ListNode* buildLinkedList(const vector<int>& values, int pos) {
    if (values.empty()) {
        return nullptr;
    }

    vector<ListNode*> nodes;
    for (int v : values) {
        nodes.push_back(new ListNode(v));
    }
    for (size_t i = 0; i + 1 < nodes.size(); ++i) {
        nodes[i]->next = nodes[i + 1];
    }
    if (pos >= 0 && pos < static_cast<int>(nodes.size())) {
        nodes.back()->next = nodes[pos];
    }
    return nodes[0];
}

inline json serializeLinkedList(ListNode* head) {
    json result = json::array();
    unordered_set<ListNode*> seen;
    while (head && !seen.count(head)) {
        seen.insert(head);
        result.push_back(head->val);
        head = head->next;
    }
    return result;
}

inline TreeNode* buildTree(const vector<optional<int>>& arr) {
    if (arr.empty() || !arr[0].has_value()) {
        return nullptr;
    }

    TreeNode* root = new TreeNode(arr[0].value());
    queue<TreeNode*> q;
    q.push(root);

    size_t i = 1;
    while (!q.empty() && i < arr.size()) {
        TreeNode* current = q.front();
        q.pop();

        if (i < arr.size() && arr[i].has_value()) {
            current->left = new TreeNode(arr[i].value());
            q.push(current->left);
        }
        i++;

        if (i < arr.size() && arr[i].has_value()) {
            current->right = new TreeNode(arr[i].value());
            q.push(current->right);
        }
        i++;
    }

    return root;
}

inline json serializeTree(TreeNode* root) {
    json result = json::array();
    if (!root) {
        return result;
    }

    queue<TreeNode*> q;
    q.push(root);
    while (!q.empty()) {
        TreeNode* node = q.front();
        q.pop();
        if (node) {
            result.push_back(node->val);
            q.push(node->left);
            q.push(node->right);
        } else {
            result.push_back(nullptr);
        }
    }
    while (!result.empty() && result.back().is_null()) {
        result.erase(result.end() - 1);
    }
    return result;
}

// ----------------------------------------------------------------------
// JSON -> argument
// ----------------------------------------------------------------------

template <typename T>
struct Arg {
    static T get(const json& j) { return j.get<T>(); }
};

template <>
struct Arg<char> {
    static char get(const json& j) {
        if (j.is_string()) {
            string s = j.get<string>();
            return s.empty() ? '\0' : s[0];
        }
        return static_cast<char>(j.get<int>());
    }
};

template <typename T>
struct Arg<vector<T>> {
    static vector<T> get(const json& j) {
        vector<T> out;
        for (const auto& item : j) {
            out.push_back(Arg<T>::get(item));
        }
        return out;
    }
};

// A list of strings may also be given as one multiline string ("N\nOP1\nOP2").
template <>
struct Arg<vector<string>> {
    static vector<string> get(const json& j) {
        if (j.is_array()) {
            return j.get<vector<string>>();
        }
        vector<string> out;
        istringstream lines(j.get<string>());
        string line;
        bool first = true;
        while (getline(lines, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            if (line.empty()) continue;
            if (first) {
                first = false;
                if (all_of(line.begin(), line.end(), ::isdigit)) continue;
            }
            out.push_back(line);
        }
        return out;
    }
};

template <>
struct Arg<TreeNode*> {
    static TreeNode* get(const json& j) {
        vector<optional<int>> values;
        for (const auto& item : j) {
            values.push_back(item.is_null() ? nullopt : optional<int>(item.get<int>()));
        }
        return buildTree(values);
    }
};

template <>
struct Arg<ListNode*> {
    static ListNode* get(const json& j) {
        return buildLinkedList(j.get<vector<int>>(), listCyclePos);
    }
};

// ----------------------------------------------------------------------
// result -> JSON
// ----------------------------------------------------------------------

template <typename T>
struct Out {
    static json to(const T& value) { return json(value); }
};

template <>
struct Out<char> {
    static json to(const char& value) { return string(1, value); }
};

template <>
struct Out<vector<bool>> {
    static json to(const vector<bool>& value) { return json(value); }
};

template <typename T>
struct Out<vector<T>> {
    static json to(const vector<T>& value) {
        json out = json::array();
        for (const auto& item : value) {
            out.push_back(Out<T>::to(item));
        }
        return out;
    }
};

template <>
struct Out<TreeNode*> {
    static json to(TreeNode* const& value) { return serializeTree(value); }
};

template <>
struct Out<ListNode*> {
    static json to(ListNode* const& value) { return serializeLinkedList(value); }
};

template <typename T>
json toJson(const T& value) {
    return Out<std::decay_t<T>>::to(value);
}

// ----------------------------------------------------------------------
// Test-case input: {"keys": [...], "values": [...]} in the order given.
// ----------------------------------------------------------------------

struct Input {
    vector<string> keys;
    vector<json> values;
    bool skipPos;

    Input(const json& payload, bool skipPos) : skipPos(skipPos) {
        keys = payload.at("keys").get<vector<string>>();
        values = payload.at("values").get<vector<json>>();
        for (size_t i = 0; i < keys.size(); ++i) {
            if (keys[i] == "pos" && values[i].is_number_integer()) {
                listCyclePos = values[i].get<int>();
            }
        }
    }

    // By parameter name when the test case uses it, otherwise by position.
    const json& arg(const string& name, size_t index) const {
        for (size_t i = 0; i < keys.size(); ++i) {
            if (keys[i] == name) return values[i];
        }
        size_t position = 0;
        for (size_t i = 0; i < keys.size(); ++i) {
            if (skipPos && keys[i] == "pos") continue;
            if (position == index) return values[i];
            position++;
        }
        throw runtime_error("missing argument: " + name);
    }
};

inline void emit(const json& output) {
    cout.flush();
    cout << RESULT_START << output.dump(-1, ' ', false, json::error_handler_t::replace) << RESULT_END << endl;
}

inline void emitError(const string& message) {
    json output;
    output["error"] = message;
    emit(output);
}

}  // namespace judge
