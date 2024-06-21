import time
import os

print("sleeping for 10000seconds")

#read environment variable
AUTH_USER_IDS = os.environ.get("AUTH_USER_IDS")
print("AUTH_USER_IDS: {}".format(AUTH_USER_IDS))
# write to file
with open("/AUTH_USER_IDS.txt", "w") as f:
    f.write(AUTH_USER_IDS)
time.sleep(10000)