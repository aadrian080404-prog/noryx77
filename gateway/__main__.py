import os

from .server import NoryxGateway
from .runtime_adapter import RuntimeAdapter
from web.app import get_runtime


def main():
    runtime = get_runtime()
    gateway = NoryxGateway(runtime_adapter=RuntimeAdapter(runtime=runtime))
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
