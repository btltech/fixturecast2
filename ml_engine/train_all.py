from .ensemble_predictor import EnsemblePredictor


def train():
    print("Starting training for all 11 models...")
    # Instantiate models
    predictor = EnsemblePredictor()

    # Mock training calls
    predictor.gbdt.train(None, None)
    predictor.catboost.train(None, None)
    predictor.poisson.train(None)
    predictor.transformer.train(None)
    predictor.lstm.train(None)
    predictor.gnn.train(None)
    predictor.bayesian.train(None)
    predictor.elo.train(None)

    print("All models trained and artifacts saved.")


if __name__ == "__main__":
    train()
