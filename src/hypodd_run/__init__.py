"""hypodd_run — a thin, domain-agnostic bridge between tabular seismic data and hypoDD.

Deliberately knows NOTHING about templates, daughter detections, match-filter output, or any
particular catalog's column names. It accepts three flat tables (see `tables.py`), writes
hypoDD's fixed-format text files, runs ph2dt/hypoDD, and reads the results back.

Everything domain-specific — which events are templates, how a lag correction is applied, where
a daughter inherits its starting location — belongs in whichever project PRODUCES the tables.
"""
__version__ = "0.1.0"
