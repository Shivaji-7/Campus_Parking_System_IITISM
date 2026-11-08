# Campus Parking Simulation

This directory contains the SUMO simulation environment for the Campus Parking Management System.

## Prerequisites
- Windows OS
- Python 3.8+
- SUMO (Simulation of Urban MObility)

## Installing SUMO on Windows
1. Download the SUMO installer from [https://eclipse.dev/sumo/](https://eclipse.dev/sumo/)
2. Run the installer and ensure SUMO is added to your PATH environment variable.
3. Set the `SUMO_HOME` environment variable to your SUMO installation directory (e.g., `C:\Program Files (x86)\Eclipse\Sumo`).

## Running the Campus Simulation
1. Open a command prompt or terminal.
2. Navigate to this directory (`simulation/`).
3. Run the basic simulation script to collect occupancy data:
   ```bash
   python run_simulation.py
   ```
4. This script uses TraCI to control SUMO step-by-step, logging data to `output/occupancy_data.csv`.

## Generating Training Data
To generate a larger synthetic dataset representing multiple days of simulated campus traffic:
1. Run the data generation script:
   ```bash
   python generate_training_data.py
   ```
2. The output will be saved to `output/training_data.csv`.

## Viewing Results in SUMO-GUI
To visualize the simulation directly:
1. Double-click the `campus.sumocfg` file, or open `sumo-gui` and load the configuration file.
2. Adjust the delay slider (e.g., to 100ms) to slow down the simulation visually.
3. Click the green 'Play' button to watch the vehicles navigate and park in their respective zones.
