from prefect import flow


@flow(log_prints=True)
def uses_emoji():
    import emoji  # type: ignore

    print(emoji.emojize("lgtm! :thumbs_up:"))  # type: ignore


if __name__ == "__main__":
    uses_emoji()
