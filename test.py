import os
os.environ["PYBLIOMETRICS_CONFIG_FILE"] = "/Users/mohammadrezagiveh/.pybliometrics/config.ini"
print("Config path being used:", os.environ["PYBLIOMETRICS_CONFIG_FILE"])

from pybliometrics.scopus import AbstractRetrieval

doi = "10.1016/j.ibusrev.2010.09.002"
ab = AbstractRetrieval(doi)

print("Title:", ab.title)
print("Abstract:", ab.abstract)
print("Journal:", ab.publicationName)
print("Date:", ab.coverDate)