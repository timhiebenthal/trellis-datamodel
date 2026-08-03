"""@bruin
name: raw.raw__customers
type: python
connection: crm_api
description: Customers pulled from the CRM API.
@bruin"""

import pandas as pd


def materialize():
    return pd.DataFrame({"customer_id": [], "customer_name": []})
