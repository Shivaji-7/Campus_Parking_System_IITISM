# ML Prediction Service

This directory contains the FastAPI-based Machine Learning prediction service for the Campus Parking Management System.

## Setup Instructions

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Training Models

Before running the service with real predictions, you need to train the models using data generated from the SUMO simulation:

1. Ensure you have run `python generate_training_data.py` in the `simulation/` directory.
2. Run the training script:
   ```bash
   python train_model.py
   ```
   This will output metrics and save `.pkl` files in the `models/` directory.

## Running the Prediction Service

Start the FastAPI application via Uvicorn:

```bash
python app.py
```
*(Or use `uvicorn app:app --reload --port 5000` for development)*

## API Endpoints

### `GET /health`
Returns the status of the service and whether models are loaded.

### `POST /predict`
Predicts the parking occupancy for a given zone and time horizon.
**Request Body (JSON):**
```json
{
    "zone_id": "zone_sac",
    "horizon": 2,
    "current_occupancy": 5
}
```
