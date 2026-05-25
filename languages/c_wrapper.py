C_WRAPPER_TEMPLATE = r"""

#include <iostream>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

using json = nlohmann::json;
using namespace std;

// ======================================================
// FUNCTION FORWARD DECLARATION (AUTO-INJECTED)
// ======================================================

extern "C" {
__FUNCTION_SIGNATURE_PLACEHOLDER__
}

json execute_one(const json& j) {

    // ==================================================
    // PARAMETER DESERIALIZATION (AUTO-GENERATED)
    // ==================================================

    __PARAMETER_DESERIALIZATION_PLACEHOLDER__

    // ==================================================
    // FUNCTION INVOCATION
    // ==================================================

    __FUNCTION_CALL_PLACEHOLDER__

    // ==================================================
    // RETURN SERIALIZATION
    // ==================================================

    json output;

    __RETURN_SERIALIZATION_PLACEHOLDER__

    return output;
}

// ======================================================
// MAIN EXECUTION ENTRY
// ======================================================

int main() {

    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input;

    if (!getline(cin, input)) {
        cout << "{\"error\":\"No input received\"}";
        return 1;
    }

    json j;

    try {
        j = json::parse(input);
    } catch (...) {
        cout << "{\"error\":\"Invalid JSON input\"}";
        return 1;
    }

    try {
        if (j.contains("test_cases")) {
            json results = json::array();
            for (const auto& tc : j["test_cases"]) {
                results.push_back(execute_one(tc["input"]));
            }
            json response;
            response["results"] = results;
            cout << response.dump();
        } else {
            cout << execute_one(j).dump();
        }
    } catch (const std::exception& e) {
        json error;
        error["error"] = e.what();
        cout << error.dump();
        return 1;
    }

    return 0;
}

// ======================================================
// USER CODE INJECTION
// ======================================================

extern "C" {
__USER_CODE_PLACEHOLDER__
}

"""
