# NORYX Test Lab — Android-only execution

The browser's **debug** build is the UI/device gate. It deliberately does not execute Python or arbitrary shell commands inside WebView.

For full repository verification on a phone, use a local Python runtime such as Termux as the execution engine and keep NORYX Browser as the dashboard/UI.

## 1. Install the runtime

Install Termux from one source only (F-Droid or the official GitHub releases). Do not mix APK/plugin sources.

Then in Termux:

```sh
pkg update
pkg install git python clang
python -m pip install --upgrade pip
python -m pip install pytest
```

## 2. Obtain NORYX7

Use your own GitHub authentication locally in Termux. Never paste a GitHub token into NORYX Browser, the repository, or chat.

```sh
git clone --branch architecture-freeze-2026-09-06 <YOUR_PRIVATE_REPOSITORY_URL>
cd noryx7-
```

## 3. Run the fixed Test Lab

The runner accepts only four predeclared targets; it does not accept arbitrary shell commands.

```sh
python devtools/test_lab/runner.py --suite compile closure completeness pytest --json > test-lab-report.json
```

A non-zero exit code means the suite is not closed.

## 4. Browser role

Install the NORYX Browser **debug** APK. Open **NORYX TEST LAB** from the debug browser and run the device gate.

The browser gate verifies the Android/WebView contract (HTTPS-only navigation, cleartext disabled, file/content access disabled, mixed content blocked, INTERNET permission).

The Python runner verifies the NORYX7 repository contract and pytest suite.

These are intentionally separate trust boundaries:

`Browser UI -> device gate`

`Termux -> fixed repository runner -> compile/closure/completeness/pytest`

The browser must never expose an arbitrary command endpoint to web content.
