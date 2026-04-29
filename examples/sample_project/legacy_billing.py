# coding: utf-8
# Legacy Billing Module - DO NOT TOUCH
# Last updated: 2014-03-15 by dev_lee (left company)
# Known issues: calculation mismatch for tier 3 boundary

import sys
import os

# Hardcoded config - should be in DB
tier1_rate = 0.15
tier2_rate = 0.22
tier3_rate = 0.35
tier4_rate = 0.50

tier1_limit = 100
tier2_limit = 300
tier3_limit = 500

def calc(cust_id, usage, month):
    """Calculate bill amount.
    cust_id: customer number
    usage: kwh used
    month: 1-12
    """
    # FIXME: seasonal multiplier not implemented
    amt = 0.0
    if usage < 0:
        print("ERROR negative usage")
        return -1

    # tier 1
    if usage <= tier1_limit:
        amt = usage * tier1_rate
    elif usage <= tier2_limit:
        amt = tier1_limit * tier1_rate + (usage - tier1_limit) * tier2_rate
    elif usage <= tier3_limit:
        amt = tier1_limit * tier1_rate + (tier2_limit - tier1_limit) * tier2_rate + (usage - tier2_limit) * tier3_rate
    else:
        amt = tier1_limit * tier1_rate + (tier2_limit - tier1_limit) * tier2_rate + (tier3_limit - tier2_limit) * tier3_rate + (usage - tier3_limit) * tier4_rate

    # apply late fee if month is old (logic unclear)
    if month < 6:
        amt = amt * 1.05

    # store in file
    f = open("/tmp/bills_" + str(cust_id) + ".txt", "a")
    f.write(str(amt) + "\n")
    f.close()

    return amt

def process_all_customers(data_list):
    # data_list is list of dicts with keys id, usage, month
    total = 0
    for d in data_list:
        a = calc(d["id"], d["usage"], d["month"])
        total = total + a
    return total

# Direct execution for cron job
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("usage: python legacy_billing.py <cust_id> <usage> <month>")
        sys.exit(1)
    result = calc(int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]))
    print("Amount: " + str(result))
