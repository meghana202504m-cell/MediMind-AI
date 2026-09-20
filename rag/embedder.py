from sentence_transformers import SentenceTransformer

_model = None


def get_model():

    global _model

    if _model is None:

        _model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

    return _model


def create_embeddings(chunks):

    model = get_model()

    return model.encode(chunks)


def create_query_embedding(query):

    model = get_model()

    return model.encode(query)