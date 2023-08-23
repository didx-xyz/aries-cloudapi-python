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

        soup = BeautifulSoup(file_read, 'xml')

        testsuite = soup.find('testsuite')
        failures = failures + int(testsuite['failures'])
        errors = errors + int(testsuite['errors'])

        testcases = soup.find_all('testcase')
        for testcase in testcases:
            class_name = testcase['classname']
            name = testcase['name']
            failure = testcase.find('failure')
