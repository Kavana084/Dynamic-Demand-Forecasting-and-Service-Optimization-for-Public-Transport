import sys
sys.path.insert(0, './backend')
from app.ml.model_loader import model_loader
model_loader.load_model()
feats = model_loader.get_feature_names()
cat_feats = model_loader.get_categorical_features()
print('Total features:', len(feats))
print('Feature list:', feats)
print()
print('Categorical features:', cat_feats)
