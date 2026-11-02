"""Snapshot SageMaker on-demand Hosting prices (us-east-2) from the AWS Price List API into evidence/pricing.json.

The Price/Latency unit costs each request as instance price x wall time; rebuild.py reads the price from this file.

  python tools/snapshot_pricing.py
"""
import datetime as dt
import json
import os

import boto3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TYPES = ["ml.g6.2xlarge", "ml.g5.2xlarge", "ml.g5.4xlarge", "ml.g6.xlarge"]


def main():
    pricing = boto3.client("pricing", region_name="us-east-1")  # the Price List API is served from us-east-1
    out = {"source": "AWS Price List API, service AmazonSageMaker, component Hosting, OnDemand, regionCode us-east-2",
           "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "usd_per_hour": {}, "sku": {}}
    for t in TYPES:
        resp = pricing.get_products(ServiceCode="AmazonSageMaker", Filters=[
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": f"{t}-Hosting"},
            {"Type": "TERM_MATCH", "Field": "regionCode", "Value": "us-east-2"}])
        (prod,) = [json.loads(p) for p in resp["PriceList"]]
        (term,) = prod["terms"]["OnDemand"].values()
        (dim,) = term["priceDimensions"].values()
        out["usd_per_hour"][t] = float(dim["pricePerUnit"]["USD"])
        out["sku"][t] = {"sku": prod["product"]["sku"], "effective_date": term["effectiveDate"], "description": dim["description"]}
    with open(os.path.join(ROOT, "evidence", "pricing.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    print(json.dumps(out["usd_per_hour"]))


if __name__ == "__main__":
    main()
