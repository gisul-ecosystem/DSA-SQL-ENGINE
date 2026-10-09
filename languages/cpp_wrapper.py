CPP_WRAPPER_TEMPLATE = r"""
#include "/opt/cpp_support.hpp"

// ======================================================
// USER CODE
// ======================================================

__USER_CODE_PLACEHOLDER__

// ======================================================
// MAIN EXECUTION ENTRY (AUTO-GENERATED)
// ======================================================

int main() {
    string _stdin_raw((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());

    json _payload;
    try {
        _payload = json::parse(_stdin_raw);
    } catch (...) {
        judge::emitError("Invalid JSON input");
        return 1;
    }

    try {
        judge::Input _in(_payload, __SKIP_POS_PLACEHOLDER__);

        __PARAMETER_DESERIALIZATION_PLACEHOLDER__

        json _output;
        __CALL_AND_SERIALIZE_PLACEHOLDER__

        judge::emit(_output);
    } catch (const exception& e) {
        judge::emitError(e.what());
        return 1;
    } catch (...) {
        judge::emitError("Unknown runtime error");
        return 1;
    }

    return 0;
}
"""
