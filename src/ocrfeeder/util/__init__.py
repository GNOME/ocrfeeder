IMAGE_TYPE = 0
TEXT_TYPE = 1
ALIGN_LEFT = 0
ALIGN_RIGHT = 1
ALIGN_CENTER = 2
ALIGN_FILL = 3

CM = 2.54
IN = 1
MM = CM*10

UNITS_DICT = {
    'cm': CM,
    'in': IN,
    'mm': MM,
}

PAPER_SIZES = {'A3': (297/MM, 420/MM),
         'A4': (210/MM, 297/MM),
         'A5': (148/MM, 210/MM),
         'B4': (250/MM, 353/MM),
         'B5': (176/MM, 250/MM),
         'B6': (125/MM, 176/MM),
         'C4': (229/MM, 324/MM),
         'C5': (162/MM, 229/MM),
         'C6': (114/MM, 162/MM),
         'Letter': (8.5, 11),
         'Legal': (8.5, 14),
         'Ledger': (17, 11),
         'Tabloid': (11, 17)
         }
