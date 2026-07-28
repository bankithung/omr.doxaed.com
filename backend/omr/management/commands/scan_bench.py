"""Measure scan accuracy and latency against a corpus of degraded captures."""

from django.core.management.base import BaseCommand

from omr import bench


class Command(BaseCommand):
    help = "Benchmark the OMR scan pipeline for accuracy and latency."

    def add_arguments(self, parser):
        parser.add_argument("-n", type=int, default=5, help="samples per case (default 5)")
        parser.add_argument("--case", default=None, help="run a single named case")
        parser.add_argument("--save", default=None, help="write one sample image per case here")

    def handle(self, *args, **o):
        results = bench.run(n_per_case=o["n"], only=o["case"], save_dir=o["save"])
        if not results:
            self.stderr.write("no cases matched")
            return
        self.stdout.write(bench.format_report(results))
