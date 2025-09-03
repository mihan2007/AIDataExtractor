# -*- coding: utf-8 -*-
from vector_store_gui import VectorStoreGUI
from uploader import upload_to_vector_store

def main():
    app = VectorStoreGUI(on_upload=upload_to_vector_store)
    app.mainloop()

if __name__ == "__main__":
    main()
