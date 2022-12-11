# Private Server Down Detector
The script is currently scanning the entire `private servers.json` database for offline servers and generatic a report.

This will allow us to get rid of the servers that are no longer operational and tidy up the relevant forum category.
## How to use
[//]: # (Check if the website is down just for you or everyone around the globe.)

* Install the latest version of [Python](https://www.python.org/downloads/), 3.11 or higher.


* Install virtual environment:
```bash
# Install virtualenv
py -3 -m venv venv

# Activate virtualenv (Windows)
./venv/scripts/activate

# Activate virtualenv (Linux)
source ./venv/bin/activate

# Install requirements
pip install -r requirements.txt
```
* Run the script:
```bash
py -3 main.py
```




