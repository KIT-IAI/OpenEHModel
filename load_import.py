import pickle


def load_obj(name):
    with open(name, "rb") as f:
        return pickle.load(f)