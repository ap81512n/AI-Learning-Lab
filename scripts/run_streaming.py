
from fde_learning_lab.ingestion import StreamingIngestionService
from fde_learning_lab.loaders import StreamingTextLoader
from pathlib import Path


def main():
    loader = StreamingTextLoader()
    service = StreamingIngestionService(loader)


    for line in service.iter_ingest("samples/example.txt"):
        print(line)


if __name__ == "__main__":
    main()
