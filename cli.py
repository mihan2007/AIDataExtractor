# -*- coding: utf-8 -*-
import argparse
from uploader import upload_to_vector_store

def main():
    parser = argparse.ArgumentParser(description="Upload files to Vector Store")
    parser.add_argument("files", nargs="+", help="Пути к файлам")
    args = parser.parse_args()
    msg = upload_to_vector_store(args.files)
    print(msg)

if __name__ == "__main__":
    main()
