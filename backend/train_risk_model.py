"""
train_risk_model.py
====================
Trains a real XGBoost model on our case data and saves it as risk_model.json.
Run this once: python train_risk_model.py
"""
import json
import os
import numpy as np

try:
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
except ImportError:
    print("Install: pip install xgboost scikit-learn numpy")
    exit(1)

# Load case data
file_path = os.path.join("src", "court_scrapers", "downloaded_cases.json")
with open(file_path, "r") as f:
    cases = json.load(f)

print(f"Loaded {len(cases)} cases for training.")

# Feature Engineering from real case data
def extract_features(case):
    status_score = 1.0 if case.get("status") == "active" else 0.0
    has_injunction = 1.0 if "injunction" in case.get("case_type", "").lower() else 0.0
    has_next_hearing = 1.0 if case.get("next_hearing") else 0.0
    case_type_score = {
        "Injunction Suit": 0.9,
        "Title Dispute": 0.8,
        "Partition Suit": 0.6,
        "Revenue Case": 0.4,
        "Civil Suit": 0.5,
    }.get(case.get("case_type", ""), 0.5)
    return [status_score, has_injunction, has_next_hearing, case_type_score]

# Build dataset
X = np.array([extract_features(c) for c in cases])
# Label: 1 = high risk (active), 0 = low risk (disposed)
y = np.array([1 if c.get("status") == "active" else 0 for c in cases])

print(f"Features shape: {X.shape}, Labels: {y.sum()} high-risk, {len(y)-y.sum()} low-risk")

# Train XGBoost
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = xgb.XGBClassifier(
    n_estimators=50,
    max_depth=3,
    learning_rate=0.1,
    use_label_encoder=False,
    eval_metric='logloss'
)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"Model Accuracy: {acc:.2%}")

# Save model
model_path = os.path.join("models", "risk_model.json")
os.makedirs("models", exist_ok=True)
model.save_model(model_path)
print(f"Model saved to: {model_path}")
print("Done! Now the advanced_engine.py will load this model automatically.")
