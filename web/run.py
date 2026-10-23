#!/usr/bin/env python3
"""
UCM raw sensor feed.

    .venv/bin/python run.py                 # real broker (must be on the mesh)
    UCM_MOCK=1 .venv/bin/python run.py      # fake nodes, no broker needed

Then open http://localhost:5002
"""

import logging

from waitress import serve

from ucm_web import mock_source, mqtt_source
from ucm_web.app import create_app
from ucm_web.config import Config
from ucm_web.store import LatestStore


def main():

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = Config.from_env()

    store = LatestStore(
        max_nodes=config.max_nodes,
        max_payload_bytes=config.max_payload_bytes,
    )

    if config.mock:
        mock_source.start(config, store)
    else:
        mqtt_source.start(config, store)

    app = create_app(store, config.source_label)

    logging.info("serving on http://%s:%d (source: %s)",
                 config.web_host, config.web_port, config.source_label)

    # waitress: a production WSGI server with a fixed thread pool, so a
    # burst of viewers queues instead of spawning unbounded threads.
    serve(app, host=config.web_host, port=config.web_port,
          threads=config.web_threads, ident="ucm-web")


if __name__ == "__main__":
    main()
