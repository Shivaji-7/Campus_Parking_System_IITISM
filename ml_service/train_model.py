import os
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

def train_and_evaluate():
    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulation", "output", "training_data.csv")
    if not os.path.exists(data_path):
        print(f"Error: Training data not found at {data_path}")
        return False

    print(f"Loading simulation dataset from {data_path}...")
    df = pd.read_csv(data_path)
    print(f"Dataset shape: {df.shape} ({len(df)} samples, {len(df.columns)} features)")

    # Define feature groups
    categorical_features = ["zone_id"]
    numerical_features = [
        "capacity", "vehicle_count", "entry_count", "exit_count",
        "traffic_density", "avg_speed_kmh",
        "hour", "day_of_week", "is_weekend", "is_peak",
        "temperature", "humidity"
    ]
    
    X = df[categorical_features + numerical_features]
    y_slots = df["occupied_slots"]
    y_pct = df["occupancy_percentage"]

    # Preprocessing
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
            ("num", "passthrough", numerical_features)
        ]
    )

    # 80/20 train/test split
    X_train, X_test, y_train, y_test, y_pct_train, y_pct_test = train_test_split(
        X, y_slots, y_pct, test_size=0.2, random_state=42, shuffle=True
    )

    print(f"Training set: {len(X_train)} samples, Test set: {len(X_test)} samples")

    # 1. Gradient Boosting Regressor (Specialized for occupancy slots)
    print("Training Gradient Boosting Model...")
    gb_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", GradientBoostingRegressor(
            n_estimators=120,
            learning_rate=0.08,
            max_depth=5,
            random_state=42
        ))
    ])
    gb_pipeline.fit(X_train, y_train)

    # 2. Random Forest Regressor (Ensemble comparison)
    print("Training Random Forest Model...")
    rf_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", RandomForestRegressor(
            n_estimators=100,
            max_depth=12,
            random_state=42,
            n_jobs=-1
        ))
    ])
    rf_pipeline.fit(X_train, y_train)

    # 3. Model for Occupancy Percentage
    print("Training Occupancy Percentage Model...")
    pct_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.08,
            max_depth=5,
            random_state=42
        ))
    ])
    pct_pipeline.fit(X_train, y_pct_train)

    # Detailed Evaluation
    gb_preds = gb_pipeline.predict(X_test)
    rf_preds = rf_pipeline.predict(X_test)
    pct_preds = pct_pipeline.predict(X_test)

    gb_mae = float(mean_absolute_error(y_test, gb_preds))
    gb_rmse = float(np.sqrt(mean_squared_error(y_test, gb_preds)))
    gb_r2 = float(r2_score(y_test, gb_preds))

    rf_mae = float(mean_absolute_error(y_test, rf_preds))
    rf_rmse = float(np.sqrt(mean_squared_error(y_test, rf_preds)))
    rf_r2 = float(r2_score(y_test, rf_preds))

    pct_mae = float(mean_absolute_error(y_pct_test, pct_preds))
    pct_rmse = float(np.sqrt(mean_squared_error(y_pct_test, pct_preds)))
    pct_r2 = float(r2_score(y_pct_test, pct_preds))

    print("\n--- Empirical Model Evaluation Results ---")
    print(f"Gradient Boosting (Slot Occupancy): MAE = {gb_mae:.3f} slots, RMSE = {gb_rmse:.3f}, R² = {gb_r2:.4f}")
    print(f"Random Forest (Slot Occupancy):     MAE = {rf_mae:.3f} slots, RMSE = {rf_rmse:.3f}, R² = {rf_r2:.4f}")
    print(f"Occupancy Percentage Model:         MAE = {pct_mae:.2f}%, RMSE = {pct_rmse:.2f}%, R² = {pct_r2:.4f}")

    # Persist Models & Metrics
    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(models_dir, exist_ok=True)

    joblib.dump(gb_pipeline, os.path.join(models_dir, "short_term_model.pkl"))
    joblib.dump(rf_pipeline, os.path.join(models_dir, "long_term_model.pkl"))
    joblib.dump(pct_pipeline, os.path.join(models_dir, "percentage_model.pkl"))

    metrics = {
        "model_name": "SUMO-Calibrated Gradient Boosting & Random Forest Regressors",
        "trained_at": datetime.now().isoformat(),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "features": categorical_features + numerical_features,
        "gradient_boosting": {
            "target": "occupied_slots",
            "mae": round(gb_mae, 4),
            "rmse": round(gb_rmse, 4),
            "r2": round(gb_r2, 4),
            "mae_interpretation": f"Predictions deviate by ~{gb_mae:.2f} slots on average across test set."
        },
        "random_forest": {
            "target": "occupied_slots",
            "mae": round(rf_mae, 4),
            "rmse": round(rf_rmse, 4),
            "r2": round(rf_r2, 4)
        },
        "percentage_model": {
            "target": "occupancy_percentage",
            "mae": round(pct_mae, 2),
            "rmse": round(pct_rmse, 2),
            "r2": round(pct_r2, 4)
        }
    }

    metrics_path = os.path.join(models_dir, "model_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nModels and empirical metrics successfully saved to {models_dir}")
    return True

if __name__ == "__main__":
    train_and_evaluate()
