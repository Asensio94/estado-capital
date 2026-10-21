import argparse
import json
import logging

from etl.run import run

parser = argparse.ArgumentParser(prog="python -m etl", description="Build data/processed from official APIs.")
parser.add_argument("--refresh", action="store_true", help="ignore the raw cache and download again")
parser.add_argument("--no-verify", action="store_true", help="skip the metadata check of dataset codes")
parser.add_argument("--s3", action="store_true", help="upload data/processed to $CAPITAL_S3_BUCKET")
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
manifest = run(refresh=args.refresh, verify=not args.no_verify, s3=args.s3)
print(json.dumps(manifest["indicators"], indent=2))
