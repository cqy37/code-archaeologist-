# Legacy utilities - shared across modules
# No tests exist for this file

def round_money(amount):
    # sometimes rounds wrong for .005
    return int(amount * 100) / 100

def format_address(addr_dict):
    # addr_dict has: street, city, province, postal
    # missing null checks caused prod crash 2015-08
    return addr_dict["street"] + ", " + addr_dict["city"] + ", " + addr_dict["province"] + " " + addr_dict["postal"]

def log_event(msg):
    # writes to shared log file with no locking
    f = open("/var/log/legacy_app.log", "a")
    f.write(msg + "\n")
    f.close()
