from bs4 import BeautifulSoup
import os

fail_json = {}
dir = "logs/containerized-tests/"
xml_files = [filename for filename in os.listdir(dir) if filename.endswith(".xml")]
