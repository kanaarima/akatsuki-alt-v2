"""Application exporter"""

import os
import time
from prometheus_client import start_http_server, Gauge, Enum, Counter
import requests
import api.database as database


class AppMetrics:
    """
    Representation of Prometheus metrics and loop to fetch and transform
    application metrics into Prometheus metrics.
    """

    def __init__(self, app_port=3983, polling_interval_seconds=5):
        self.app_port = app_port
        self.polling_interval_seconds = polling_interval_seconds
        # Prometheus metrics to collect
        self.total_beatmaps = Gauge("total_beatmaps", "Total Beatmaps")
        self.akatsuki_beatmaps = Gauge("akatsuki_beatmaps", "Akatsuki Beatmaps")
        self.bancho_beatmaps = Gauge("bancho_beatmaps", "Bancho Beatmaps")
        self.requests = Gauge("requests", "Requests")

    def run_metrics_loop(self):
        """Metrics fetching loop"""

        while True:
            self.fetch()
            time.sleep(self.polling_interval_seconds)

    def fetch(self):
        """
        Get metrics from application and refresh Prometheus metrics with
        new values.
        """
        self.total_beatmaps.set(
            database.conn.execute("SELECT COUNT(beatmap_id) FROM beatmaps").fetchall()[
                0
            ][0]
        )
        self.akatsuki_beatmaps.set(
            database.conn.execute(
                "SELECT COUNT(beatmap_id) FROM beatmaps WHERE akatsuki_status BETWEEN 1 AND 4 AND bancho_status BETWEEN -2 AND 0"
            ).fetchall()[0][0]
        )
        self.bancho_beatmaps.set(
            database.conn.execute(
                "SELECT COUNT(beatmap_id) FROM beatmaps WHERE bancho_status BETWEEN 1 AND 4"
            ).fetchall()[0][0]
        )
        self.requests.set(
            database.conn.execute(
                'SELECT requests FROM metrics WHERE endpoint = "global"'
            ).fetchall()[0][0]
        )


def main():
    """Main entry point"""

    polling_interval_seconds = int(os.getenv("POLLING_INTERVAL_SECONDS", "5"))
    app_port = int(os.getenv("APP_PORT", "80"))
    exporter_port = int(os.getenv("EXPORTER_PORT", "9877"))

    app_metrics = AppMetrics(
        app_port=app_port, polling_interval_seconds=polling_interval_seconds
    )
    start_http_server(exporter_port)
    app_metrics.run_metrics_loop()


if __name__ == "__main__":
    main()
