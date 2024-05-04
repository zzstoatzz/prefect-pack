import re

from flows.hello import print_info


def test_print_info(caplog):
    with caplog.at_level("INFO"):
        print_info()

    assert re.search(r"Python version: \d+\.\d+\.\d+", caplog.text)
    assert re.search(r"Platform: .+", caplog.text)
    assert re.search(r"Prefect version: .+", caplog.text)
