CPP_WRAPPER_TEMPLATE = r"""

#include "/opt/cpp_support.hpp"

// ======================================================
// FUNCTION FORWARD DECLARATION (AUTO-INJECTED)
// ======================================================

__FUNCTION_SIGNATURE_PLACEHOLDER__

// ======================================================
// MAIN EXECUTION ENTRY
// ======================================================

int main() {
    try {
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

        // ==================================================
        // PARAMETER DESERIALIZATION (AUTO-GENERATED)
        // ==================================================

        __PARAMETER_DESERIALIZATION_PLACEHOLDER__

        // ==================================================
        // FUNCTION INVOCATION
        // ==================================================

        auto result = __FUNCTION_NAME_PLACEHOLDER__(
            __FUNCTION_ARGUMENT_LIST_PLACEHOLDER__
        );

        // ==================================================
        // RETURN TYPE SERIALIZATION
        // ==================================================

        json output;

        __RETURN_SERIALIZATION_PLACEHOLDER__

        cout << output.dump();

    } catch (const exception& e) {
        cout << "{\"error\":\"" << e.what() << "\"}";
        return 1;
    } catch (...) {
        cout << "{\"error\":\"Unknown runtime error\"}";
        return 1;
    }

    return 0;
}

// ======================================================
// USER CODE INJECTION
// ======================================================

__USER_CODE_PLACEHOLDER__

"""
