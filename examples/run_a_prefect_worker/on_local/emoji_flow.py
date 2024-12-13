from prefect import flow


@flow(log_prints=True)
def uses_emoji():
    import emoji

    print(emoji.emojize("lgtm! :thumbs_up:"))


if __name__ == "__main__":
    uses_emoji()
