import os
import sys

# Make the `invoicely` package importable when pytest runs from the fixture dir.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
