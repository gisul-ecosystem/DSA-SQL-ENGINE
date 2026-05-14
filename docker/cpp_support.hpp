#include <iostream>
#include <optional>
#include <queue>
#include <stdexcept>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

using json = nlohmann::json;
using namespace std;

struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x) : val(x), next(nullptr) {}
};

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

inline ListNode* buildLinkedList(const vector<int>& values) {
    if (values.empty()) {
        return nullptr;
    }

    ListNode* head = new ListNode(values[0]);
    ListNode* current = head;

    for (size_t i = 1; i < values.size(); ++i) {
        current->next = new ListNode(values[i]);
        current = current->next;
    }

    return head;
}

inline vector<int> serializeLinkedList(ListNode* head) {
    vector<int> result;
    while (head) {
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

    int i = 1;
    while (!q.empty() && i < static_cast<int>(arr.size())) {
        TreeNode* current = q.front();
        q.pop();

        if (i < static_cast<int>(arr.size()) && arr[i].has_value()) {
            current->left = new TreeNode(arr[i].value());
            q.push(current->left);
        }
        i++;

        if (i < static_cast<int>(arr.size()) && arr[i].has_value()) {
            current->right = new TreeNode(arr[i].value());
            q.push(current->right);
        }
        i++;
    }

    return root;
}

inline json serializeTree(TreeNode* root) {
    if (!root) {
        return json::array();
    }

    vector<optional<int>> temp;
    queue<TreeNode*> q;
    q.push(root);

    while (!q.empty()) {
        TreeNode* node = q.front();
        q.pop();

        if (node) {
            temp.push_back(node->val);
            q.push(node->left);
            q.push(node->right);
        } else {
            temp.push_back(nullopt);
        }
    }

    while (!temp.empty() && !temp.back().has_value()) {
        temp.pop_back();
    }

    json result = json::array();
    for (const auto& value : temp) {
        if (value.has_value()) {
            result.push_back(value.value());
        } else {
            result.push_back(nullptr);
        }
    }
    return result;
}
