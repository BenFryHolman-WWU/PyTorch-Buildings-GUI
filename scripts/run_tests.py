#!/usr/bin/env python3
import argparse
import io
import os
import sys
import time
import unittest
from pathlib import Path

from tqdm import tqdm


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"


class ProgressResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity, progress):
        super().__init__(stream, descriptions, verbosity)
        self.progress = progress
        self.start_times = {}

    def startTest(self, test):
        self.start_times[test] = time.perf_counter()
        self.progress.set_description_str(self.getDescription(test)[:80])
        super().startTest(test)

    def stopTest(self, test):
        elapsed = time.perf_counter() - self.start_times.pop(test, time.perf_counter())
        status = "ok"
        if self.failures and self.failures[-1][0] is test:
            status = "FAIL"
        elif self.errors and self.errors[-1][0] is test:
            status = "ERROR"
        elif self.skipped and self.skipped[-1][0] is test:
            status = "SKIP"
        elif self.expectedFailures and self.expectedFailures[-1][0] is test:
            status = "expected-fail"
        elif self.unexpectedSuccesses and self.unexpectedSuccesses[-1] is test:
            status = "unexpected-success"
        self.progress.set_postfix_str(f"{status} {elapsed:.2f}s", refresh=False)
        self.progress.update(1)
        super().stopTest(test)


class ProgressRunner(unittest.TextTestRunner):
    resultclass = ProgressResult

    def __init__(self, *args, progress=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress = progress

    def _makeResult(self):
        return self.resultclass(self.stream, self.descriptions, self.verbosity, self.progress)


def flatten_suite(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten_suite(item)
        else:
            yield item


def main():
    parser = argparse.ArgumentParser(description="Run the PyTorch Buildings GUI test suite.")
    parser.add_argument(
        "pattern",
        nargs="?",
        default="test*.py",
        help="unittest discovery pattern, default: test*.py",
    )
    parser.add_argument("-v", "--verbose", action="count", default=0, help="show unittest details")
    args = parser.parse_args()

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts=false")
    os.environ.setdefault("MPLCONFIGDIR", "/private/tmp")

    for path in (ROOT / "src", ROOT / "neuromancer_repo" / "src", TESTS_DIR):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)

    suite = unittest.defaultTestLoader.discover(str(TESTS_DIR), pattern=args.pattern)
    tests = list(flatten_suite(suite))
    if not tests:
        print(f"No tests discovered in {TESTS_DIR} with pattern {args.pattern!r}.", file=sys.stderr)
        return 1

    print(f"Discovered {len(tests)} tests.")
    rediscovered_suite = unittest.TestSuite(tests)
    stream = sys.stderr if args.verbose else io.StringIO()
    with tqdm(total=len(tests), unit="test", dynamic_ncols=True, colour="green") as progress:
        runner = ProgressRunner(verbosity=args.verbose, progress=progress, stream=stream)
        result = runner.run(rediscovered_suite)

    print()
    if not result.wasSuccessful():
        for label, entries in (("FAIL", result.failures), ("ERROR", result.errors)):
            for test, traceback_text in entries:
                print(f"{label}: {test.id()}")
                print(traceback_text)
    print(
        f"Ran {result.testsRun} tests: "
        f"{len(result.failures)} failed, {len(result.errors)} errored, "
        f"{len(result.skipped)} skipped."
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
