import schedule
import time
import subprocess

def run_update_user_data():
    subprocess.run(["python3", "update_user_data.py"])

schedule.every().day.at("05:00").do(run_update_user_data)

while True:
    schedule.run_pending()
    time.sleep(60)
