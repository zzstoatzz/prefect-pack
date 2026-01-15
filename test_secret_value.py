import os

from prefect import flow


@flow
def test_secret_injection():
    """test if secret block .value attribute works in prefect.yaml"""
    test_secret = os.getenv("TEST_SECRET")
    print(f"TEST_SECRET value: {test_secret}")
    print(f"TEST_SECRET type: {type(test_secret)}")

    if test_secret == "my-secret-value":
        print("✓ Secret injection worked correctly!")
    else:
        print(f"✗ Expected 'my-secret-value', got: {test_secret}")

    return test_secret


if __name__ == "__main__":
    test_secret_injection()
