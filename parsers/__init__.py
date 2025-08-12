# parsers/__init__.py

"""
Dieses Paket sammelt alle spezialisierten Q-DAS-Parser.
Die PARSER_CHAIN definiert die Reihenfolge, in der sie versucht werden.
"""
from . import bosch_parser
from . import messdate_parser

PARSER_CHAIN = [
    bosch_parser.parse,
    messdate_parser.parse,
]