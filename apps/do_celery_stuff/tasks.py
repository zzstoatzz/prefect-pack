import math

from prefect import task
from prefect.artifacts import Artifact


@task(persist_result=True, log_prints=True)
def find_primes_up_to(n: int) -> list[int]:
    """
    Find prime numbers up to n.
    """

    def is_prime(n: int) -> bool:
        if n <= 1:
            return False
        for i in range(2, int(math.sqrt(n)) + 1):
            if n % i == 0:
                return False
        return True

    primes = []
    for i in range(2, n + 1):
        if is_prime(i):
            primes.append(i)

    Artifact.get_or_create(key=f"primes-up-to-{n}", data=primes, _sync=True)
    return primes


if __name__ == "__main__":
    find_primes_up_to.serve()
