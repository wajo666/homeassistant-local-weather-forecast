"""Simple test runner to verify elevation tests work."""
import subprocess
import sys

def run_test(test_name):
    """Run a single test and return result."""
    cmd = [
        sys.executable, "-m", "pytest",
        f"tests/test_config_flow.py::{test_name}",
        "-v", "--tb=short"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0, result.stdout + result.stderr

if __name__ == "__main__":
    tests_to_run = [
        "TestConfigFlow::test_form_invalid_elevation_too_low",
        "TestConfigFlow::test_form_invalid_elevation_too_high",
        "TestOptionsFlow::test_options_flow_invalid_elevation",
    ]

    print("Running elevation validation tests...")
    print("=" * 60)

    results = {}
    for test in tests_to_run:
        print(f"\nRunning: {test}")
        try:
            passed, output = run_test(test)
            results[test] = passed
            if passed:
                print(f"✓ PASSED")
            else:
                print(f"✗ FAILED")
                print("Output:", output[-500:] if len(output) > 500 else output)
        except Exception as e:
            print(f"✗ ERROR: {e}")
            results[test] = False

    print("\n" + "=" * 60)
    print("SUMMARY:")
    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test.split('::')[1]}")

    all_passed = all(results.values())
    print("\n" + ("ALL TESTS PASSED!" if all_passed else "SOME TESTS FAILED"))
    sys.exit(0 if all_passed else 1)

