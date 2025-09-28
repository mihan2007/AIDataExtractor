# -*- coding: utf-8 -*-
from pathlib import Path
import sys

if __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from ui.vector_store_gui import VectorStoreGUI


def main():
    app = VectorStoreGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
