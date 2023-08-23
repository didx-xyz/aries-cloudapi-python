from bs4 import BeautifulSoup
import os

fail_json = {}
dir = "logs/containerized-tests/"
xml_files = [filename for filename in os.listdir(dir) if filename.endswith(".xml")]
failures = 0
errors = 0

for xml_file in xml_files:
    file_path = os.path.join(dir, xml_file)
    with open(file_path,"r") as file_read:
