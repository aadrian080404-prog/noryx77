# NORYX Test Lab

Temporary, local-only development test harness. It is not part of the NORYX7 runtime and must never be shipped as a production dependency.

The lab is provider-independent: it runs repository checks without GitHub Actions or cloud CI. On Android, a local Python environment such as Termux can execute the Python verification suite. The browser may later expose a debug dashboard, but execution remains outside WebView.

## Phone-first usage

From the repository root:

```text
python -m devtools.test_lab.runner
```

For a smaller structural pass:

```text
python -m devtools.test_lab.runner --suite compile closure completeness
```

The runner emits JSON using schema `noryx7/test-lab/v1` and exits non-zero on the first failed target. It never accepts arbitrary shell commands.

## Security rules

- any future HTTP control endpoint must bind to loopback only;
- never accept arbitrary shell commands from the browser;
- whitelist test targets;
- keep production secrets and keys inaccessible;
- enforce timeouts and bounded output;
- do not import this package from production runtime code;
- remove the lab before production packaging.

The Android browser itself remains a separate WebView application. Test Lab is a development aid, not a NORYX7 runtime dependency.