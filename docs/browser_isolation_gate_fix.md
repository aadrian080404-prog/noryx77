# NORYX Browser isolation gate — boundary fix

The standalone browser may contain a network client for the NORYX Gateway. It must not contain direct cognitive/runtime/provider integration.

The isolation scanner therefore:

- excludes generated Android/Gradle directories such as `build/` and `.gradle/`;
- ignores comments and string literals when looking for direct integration markers, so documentation and endpoint/resource values do not become false positives;
- continues to inspect executable/import-level source for forbidden direct integrations such as HYPERSYNTH, model providers, chatbot implementations, telemetry/tracking and `addJavascriptInterface`.

This is a gate correction, not a relaxation of the browser/runtime boundary: Browser -> Gateway is allowed; Browser -> HYPERSYNTH/provider/runtime internals is not.
