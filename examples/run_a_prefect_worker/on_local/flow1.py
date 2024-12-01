from prefect import flow


@flow
def uses_emoji():
    import os

    print(os.environ["VIRTUAL_ENV"])
    print(os.environ["PATH"])
    import emoji

    print(emoji.emojize("Hello, World! :smile:"))


if __name__ == "__main__":
    uses_emoji()
