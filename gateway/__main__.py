import os

from .server import NoryxGateway


def main():
    gateway = NoryxGateway()
    gateway.serve(
        host=os.environ.get(
            "NORYX_GATEWAY_HOST",
            "0.0.0.0",
        ),
        port=int(
            os.environ.get(
                "NORYX_GATEWAY_PORT",
                "8787",
            )
        ),
    )


if __name__ == "__main__":
    main()
