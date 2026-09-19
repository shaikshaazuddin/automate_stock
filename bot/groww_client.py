import os

from growwapi import GrowwAPI


def connect():
    r = GrowwAPI.get_access_token(api_key=os.environ["GROWW_API_KEY"],
                                  secret=os.environ["GROWW_API_SECRET"])
    token = r.get("token") or r.get("access_token") if isinstance(r, dict) else r
    return GrowwAPI(token)
